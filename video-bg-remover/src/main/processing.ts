import { join } from 'path'
import { tmpdir } from 'os'
import { mkdirSync, readdirSync, existsSync } from 'fs'
import { randomUUID } from 'crypto'
import { extractFrames, extractAudio, assembleVideo, getVideoInfo } from './ffmpeg'
import { getModelPath } from './model-download'
import { fork, ChildProcess, execSync } from 'child_process'
import { app } from 'electron'

// Recycle worker every N frames to prevent native memory accumulation
const FRAMES_PER_WORKER = 100

let cancelled = false
let workerProcess: ChildProcess | null = null

export function cancelProcessing(): void {
  cancelled = true
  if (workerProcess) {
    try { workerProcess.kill() } catch {}
    workerProcess = null
  }
}

function getWorkerPath(): string {
  const workerName = 'worker.js'
  // When using system node, worker must be outside asar (unpacked)
  const unpackedPath = join(
    app.getAppPath().replace('app.asar', 'app.asar.unpacked'),
    'out', 'main', workerName
  )
  if (existsSync(unpackedPath)) return unpackedPath

  const candidates = [
    join(__dirname, workerName),
    join(app.getAppPath(), 'out', 'main', workerName)
  ]
  for (const p of candidates) {
    if (existsSync(p)) return p
  }
  return candidates[0]
}

interface WorkerHandle {
  process: ChildProcess
  dead: boolean
  exitError: Error | null
  stderr: string
}

function findSystemNode(): string {
  // Electron's binary crashes with BiRefNet's ARM convolution kernels,
  // so we use the system Node.js binary for the worker process
  const candidates = [
    '/usr/local/bin/node',
    '/opt/homebrew/bin/node',
    '/usr/bin/node'
  ]
  for (const p of candidates) {
    if (existsSync(p)) return p
  }
  // Fallback: try to find via PATH
  try {
    const found = execSync('which node', { encoding: 'utf8' }).trim()
    if (found) return found
  } catch {}
  // Last resort: use Electron as node
  return process.execPath
}

function spawnWorker(workerPath: string): WorkerHandle {
  const nodePath = findSystemNode()
  const unpackedModules = join(
    app.getAppPath().replace('app.asar', 'app.asar.unpacked'),
    'node_modules'
  )
  console.log('[processing] Using node binary:', nodePath)
  console.log('[processing] NODE_PATH:', unpackedModules)
  const handle: WorkerHandle = {
    process: fork(workerPath, [], {
      stdio: ['pipe', 'pipe', 'pipe', 'ipc'],
      execPath: nodePath,
      env: {
        ...process.env,
        ELECTRON_RUN_AS_NODE: undefined,
        NODE_PATH: unpackedModules
      },
      execArgv: ['--expose-gc', '--max-old-space-size=4096']
    }),
    dead: false,
    exitError: null,
    stderr: ''
  }

  handle.process.stderr?.on('data', (chunk: Buffer) => {
    handle.stderr += chunk.toString()
    console.log('[worker stderr]', chunk.toString().trim())
  })
  handle.process.stdout?.on('data', (chunk: Buffer) => {
    console.log('[worker stdout]', chunk.toString().trim())
  })
  handle.process.on('exit', (code, signal) => {
    handle.dead = true
    if (code !== 0 && code !== null) {
      handle.exitError = new Error(
        `Worker crashed (code=${code}, signal=${signal})${handle.stderr ? ': ' + handle.stderr.slice(-500) : ''}`
      )
    }
    console.log(`[processing] Worker exited: code=${code}, signal=${signal}`)
  })

  return handle
}

async function waitForWorkerReady(handle: WorkerHandle): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(() => {
      reject(new Error(`Worker startup timeout. stderr: ${handle.stderr}`))
    }, 60000)

    handle.process.once('message', (msg: any) => {
      if (msg.type === 'ready') {
        clearTimeout(timeout)
        resolve()
      }
    })
    handle.process.once('error', (err) => {
      clearTimeout(timeout)
      reject(new Error(`Worker error: ${err.message}. stderr: ${handle.stderr}`))
    })
    if (handle.dead) {
      clearTimeout(timeout)
      reject(handle.exitError || new Error('Worker died before ready'))
    }
  })
}

async function stopWorker(handle: WorkerHandle): Promise<void> {
  if (handle.dead) return
  try {
    handle.process.send({ type: 'exit' })
    await new Promise<void>((resolve) => {
      const t = setTimeout(() => {
        try { handle.process.kill() } catch {}
        resolve()
      }, 5000)
      handle.process.once('exit', () => { clearTimeout(t); resolve() })
    })
  } catch {
    try { handle.process.kill() } catch {}
  }
}

async function processFrameWithWorker(
  handle: WorkerHandle,
  framePath: string,
  outputPath: string,
  index: number,
  modelPath: string,
  backgroundType: string,
  backgroundColor: string
): Promise<void> {
  if (handle.dead) throw handle.exitError || new Error('Worker is dead')

  return new Promise<void>((resolve, reject) => {
    const onMessage = (msg: any) => {
      if (msg.index !== index) return
      handle.process.removeListener('message', onMessage)
      handle.process.removeListener('exit', onExit)
      if (msg.type === 'frame-done') {
        resolve()
      } else if (msg.type === 'frame-error') {
        reject(new Error(msg.error))
      }
    }
    const onExit = (code: number | null) => {
      handle.process.removeListener('message', onMessage)
      reject(new Error(`Worker crashed during frame ${index} (exit code ${code})`))
    }

    handle.process.on('message', onMessage)
    handle.process.once('exit', onExit)
    handle.process.send({
      type: 'process-frame',
      framePath,
      outputPath,
      index,
      modelPath,
      backgroundType,
      backgroundColor
    })
  })
}

export async function processVideo(
  inputPath: string,
  backgroundType: 'transparent' | 'color',
  backgroundColor: string,
  onProgress: (progress: number, message: string) => void
): Promise<string> {
  cancelled = false

  const workDir = join(tmpdir(), `vbr-${randomUUID()}`)
  const framesDir = join(workDir, 'frames')
  const outputFramesDir = join(workDir, 'output-frames')
  const audioPath = join(workDir, 'audio.aac')

  mkdirSync(framesDir, { recursive: true })
  mkdirSync(outputFramesDir, { recursive: true })

  let currentWorker: WorkerHandle | null = null

  try {
    onProgress(0, 'Analyzing video...')
    const videoInfo = await getVideoInfo(inputPath)

    onProgress(5, 'Extracting frames...')
    await extractFrames(inputPath, framesDir)

    onProgress(10, 'Extracting audio...')
    let hasAudio = true
    try {
      await extractAudio(inputPath, audioPath)
    } catch {
      hasAudio = false
    }

    const frameFiles = readdirSync(framesDir)
      .filter((f) => f.endsWith('.png'))
      .sort()
    const totalFrames = frameFiles.length
    const modelPath = getModelPath()
    const workerPath = getWorkerPath()
    console.log('[processing] Worker path:', workerPath, 'exists:', existsSync(workerPath))
    console.log('[processing] Total frames:', totalFrames, `(recycling worker every ${FRAMES_PER_WORKER} frames)`)

    let framesInCurrentWorker = 0

    for (let i = 0; i < totalFrames; i++) {
      if (cancelled) throw new Error('CANCELLED')

      // Spawn or recycle worker
      if (!currentWorker || currentWorker.dead || framesInCurrentWorker >= FRAMES_PER_WORKER) {
        if (currentWorker && !currentWorker.dead) {
          console.log(`[processing] Recycling worker after ${framesInCurrentWorker} frames`)
          onProgress(
            15 + Math.round(((i) / totalFrames) * 75),
            `Recycling worker (memory cleanup)... frame ${i}/${totalFrames}`
          )
          await stopWorker(currentWorker)
        }

        console.log(`[processing] Spawning new worker for frames ${i}+`)
        currentWorker = spawnWorker(workerPath)
        workerProcess = currentWorker.process
        await waitForWorkerReady(currentWorker)
        framesInCurrentWorker = 0
      }

      const framePath = join(framesDir, frameFiles[i])
      const outputFramePath = join(outputFramesDir, frameFiles[i])

      await processFrameWithWorker(
        currentWorker,
        framePath,
        outputFramePath,
        i,
        modelPath,
        backgroundType,
        backgroundColor
      )

      framesInCurrentWorker++
      const frameProgress = 15 + Math.round(((i + 1) / totalFrames) * 75)
      onProgress(frameProgress, `Processing frame ${i + 1} of ${totalFrames}...`)
    }

    // Stop final worker
    if (currentWorker && !currentWorker.dead) {
      await stopWorker(currentWorker)
    }
    workerProcess = null

    onProgress(92, 'Assembling video...')
    const ext = backgroundType === 'transparent' ? 'webm' : 'mp4'
    const outputPath = join(workDir, `output.${ext}`)
    await assembleVideo(
      outputFramesDir,
      hasAudio ? audioPath : null,
      outputPath,
      videoInfo.fps,
      backgroundType === 'transparent'
    )

    onProgress(100, 'Done!')
    return outputPath
  } catch (error) {
    if (currentWorker && !currentWorker.dead) {
      try { currentWorker.process.kill() } catch {}
    }
    workerProcess = null
    throw error
  }
}
