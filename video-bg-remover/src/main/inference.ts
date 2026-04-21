import * as ort from 'onnxruntime-node'
import sharp from 'sharp'
import { getModelPath } from './model-download'

let session: ort.InferenceSession | null = null

async function getSession(): Promise<ort.InferenceSession> {
  if (!session) {
    const modelPath = getModelPath()
    session = await ort.InferenceSession.create(modelPath, {
      executionProviders: ['cpu'],
      graphOptimizationLevel: 'all'
    })
  }
  return session
}

export async function runInference(imagePath: string): Promise<Buffer> {
  const sess = await getSession()

  // RMBG-1.4 expects 1024x1024 RGB input, normalized to [0, 1]
  const inputSize = 1024

  const { data: rawPixels, info } = await sharp(imagePath)
    .resize(inputSize, inputSize, { fit: 'fill' })
    .removeAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true })

  // Normalize to [0,1] and convert to CHW format (channels first)
  const floatData = new Float32Array(3 * inputSize * inputSize)
  const mean = [0.485, 0.456, 0.406]
  const std = [0.229, 0.224, 0.225]

  for (let i = 0; i < inputSize * inputSize; i++) {
    floatData[i] = (rawPixels[i * 3] / 255 - mean[0]) / std[0]                         // R
    floatData[inputSize * inputSize + i] = (rawPixels[i * 3 + 1] / 255 - mean[1]) / std[1] // G
    floatData[2 * inputSize * inputSize + i] = (rawPixels[i * 3 + 2] / 255 - mean[2]) / std[2] // B
  }

  const inputTensor = new ort.Tensor('float32', floatData, [1, 3, inputSize, inputSize])

  const inputName = sess.inputNames[0]
  const results = await sess.run({ [inputName]: inputTensor })

  const outputName = sess.outputNames[0]
  const outputTensor = results[outputName]
  const outputData = outputTensor.data as Float32Array

  // Convert output to grayscale mask (0-255)
  const maskSize = Math.sqrt(outputData.length)
  const maskPixels = Buffer.alloc(maskSize * maskSize)

  // Find min/max for normalization
  let min = Infinity
  let max = -Infinity
  for (let i = 0; i < outputData.length; i++) {
    if (outputData[i] < min) min = outputData[i]
    if (outputData[i] > max) max = outputData[i]
  }
  const range = max - min || 1

  for (let i = 0; i < outputData.length; i++) {
    maskPixels[i] = Math.round(((outputData[i] - min) / range) * 255)
  }

  // Return mask as PNG buffer
  const maskBuffer = await sharp(maskPixels, {
    raw: { width: maskSize, height: maskSize, channels: 1 }
  })
    .png()
    .toBuffer()

  return maskBuffer
}

export function disposeSession(): void {
  session = null
}
