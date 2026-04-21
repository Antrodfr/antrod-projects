// Worker process for video background removal
// Runs in a separate Node.js process to isolate native crashes and memory

const ort = require('onnxruntime-node')
const sharp = require('sharp')
const path = require('path')
const fs = require('fs')

sharp.cache(false)
sharp.concurrency(1)

let session = null

async function getSession(modelPath) {
  if (!session) {
    console.log('[worker] Loading model:', modelPath)
    session = await ort.InferenceSession.create(modelPath, {
      executionProviders: ['cpu'],
      graphOptimizationLevel: 'all',
      intraOpNumThreads: 1,
      interOpNumThreads: 1
    })
    console.log('[worker] Model loaded')
  }
  return session
}

async function runInference(sess, imagePath) {
  const inputSize = 1024

  // Use 'contain' to preserve aspect ratio (pad with black) instead of 'fill' which stretches
  const { data: rawPixels } = await sharp(imagePath)
    .resize(inputSize, inputSize, { fit: 'contain', background: { r: 0, g: 0, b: 0 } })
    .removeAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true })

  const floatData = new Float32Array(3 * inputSize * inputSize)
  const mean = [0.485, 0.456, 0.406]
  const std = [0.229, 0.224, 0.225]

  for (let i = 0; i < inputSize * inputSize; i++) {
    floatData[i] = (rawPixels[i * 3] / 255 - mean[0]) / std[0]
    floatData[inputSize * inputSize + i] = (rawPixels[i * 3 + 1] / 255 - mean[1]) / std[1]
    floatData[2 * inputSize * inputSize + i] = (rawPixels[i * 3 + 2] / 255 - mean[2]) / std[2]
  }

  const inputTensor = new ort.Tensor('float32', floatData, [1, 3, inputSize, inputSize])
  const results = await sess.run({ [sess.inputNames[0]]: inputTensor })
  // Use last output (BiRefNet may have multiple intermediate stage outputs)
  const outputKey = sess.outputNames[sess.outputNames.length - 1]
  const outputData = results[outputKey].data

  // Apply sigmoid then normalize to 0-255
  const maskSize = Math.round(Math.sqrt(outputData.length))
  const maskPixels = Buffer.alloc(maskSize * maskSize)
  for (let i = 0; i < outputData.length; i++) {
    const sig = 1 / (1 + Math.exp(-outputData[i]))
    maskPixels[i] = Math.round(sig * 255)
  }

  return sharp(maskPixels, { raw: { width: maskSize, height: maskSize, channels: 1 } })
    .png()
    .toBuffer()
}

async function compositeFrame(framePath, maskBuffer, outputPath, backgroundType, backgroundColor) {
  const metadata = await sharp(framePath).metadata()
  const width = metadata.width
  const height = metadata.height

  // Crop the mask to remove padding added by 'contain' resize, then resize to original dimensions
  const inputSize = 1024
  const scale = Math.min(inputSize / width, inputSize / height)
  const scaledW = Math.round(width * scale)
  const scaledH = Math.round(height * scale)
  const left = Math.round((inputSize - scaledW) / 2)
  const top = Math.round((inputSize - scaledH) / 2)

  const resizedMask = await sharp(maskBuffer)
    .extract({ left, top, width: scaledW, height: scaledH })
    .resize(width, height, { fit: 'fill' })
    .grayscale()
    .raw()
    .toBuffer()

  const rawFrame = await sharp(framePath).removeAlpha().raw().toBuffer()

  if (backgroundType === 'transparent') {
    const outputPixels = Buffer.alloc(width * height * 4)
    for (let i = 0; i < width * height; i++) {
      outputPixels[i * 4] = rawFrame[i * 3]
      outputPixels[i * 4 + 1] = rawFrame[i * 3 + 1]
      outputPixels[i * 4 + 2] = rawFrame[i * 3 + 2]
      outputPixels[i * 4 + 3] = resizedMask[i]
    }
    await sharp(outputPixels, { raw: { width, height, channels: 4 } })
      .png()
      .toFile(outputPath)
  } else {
    const r = parseInt(backgroundColor.slice(1, 3), 16)
    const g = parseInt(backgroundColor.slice(3, 5), 16)
    const b = parseInt(backgroundColor.slice(5, 7), 16)

    const outputPixels = Buffer.alloc(width * height * 3)
    for (let i = 0; i < width * height; i++) {
      const a = resizedMask[i] / 255
      outputPixels[i * 3] = Math.round(rawFrame[i * 3] * a + r * (1 - a))
      outputPixels[i * 3 + 1] = Math.round(rawFrame[i * 3 + 1] * a + g * (1 - a))
      outputPixels[i * 3 + 2] = Math.round(rawFrame[i * 3 + 2] * a + b * (1 - a))
    }
    await sharp(outputPixels, { raw: { width, height, channels: 3 } })
      .png()
      .toFile(outputPath)
  }
}

let frameCount = 0

async function main() {
  process.on('uncaughtException', (err) => {
    console.error('[worker] Uncaught exception:', err)
    try {
      process.send({ type: 'frame-error', index: -1, error: 'Worker crashed: ' + err.message })
    } catch {}
    process.exit(1)
  })

  process.on('message', async (msg) => {
    if (msg.type === 'process-frame') {
      try {
        const sess = await getSession(msg.modelPath)
        const maskBuffer = await runInference(sess, msg.framePath)
        await compositeFrame(msg.framePath, maskBuffer, msg.outputPath, msg.backgroundType, msg.backgroundColor)

        // Delete source frame to save disk space
        try { fs.unlinkSync(msg.framePath) } catch {}

        frameCount++
        // Periodically force GC if available
        if (frameCount % 50 === 0 && global.gc) {
          global.gc()
        }

        process.send({ type: 'frame-done', index: msg.index })
      } catch (err) {
        console.error('[worker] Frame error:', err)
        process.send({ type: 'frame-error', index: msg.index, error: err.message })
      }
    } else if (msg.type === 'exit') {
      console.log('[worker] Received exit signal, cleaning up...')
      if (session) {
        try { await session.release() } catch {}
        session = null
      }
      process.exit(0)
    }
  })

  process.send({ type: 'ready' })
}

main()
