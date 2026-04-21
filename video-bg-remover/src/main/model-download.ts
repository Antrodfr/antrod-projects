import { app } from 'electron'
import { join } from 'path'
import { existsSync, mkdirSync, createWriteStream, renameSync, unlinkSync, readdirSync } from 'fs'
import https from 'https'
import http from 'http'

const MODEL_URL =
  'https://huggingface.co/onnx-community/BiRefNet_lite-ONNX/resolve/main/onnx/model.onnx'
const MODEL_DIR = join(app.getPath('userData'), 'models')
const MODEL_FILENAME = 'birefnet-lite.onnx'
const MODEL_PATH = join(MODEL_DIR, MODEL_FILENAME)

// Remove old model files that are no longer used
export function cleanupOldModels(): void {
  if (!existsSync(MODEL_DIR)) return
  try {
    for (const file of readdirSync(MODEL_DIR)) {
      if (file.endsWith('.onnx') && file !== MODEL_FILENAME) {
        console.log('[model] Removing old model:', file)
        try { unlinkSync(join(MODEL_DIR, file)) } catch {}
      }
    }
  } catch {}
}

export function getModelPath(): string {
  return MODEL_PATH
}

export function getModelStatus(): { downloaded: boolean; path: string } {
  return {
    downloaded: existsSync(MODEL_PATH),
    path: MODEL_PATH
  }
}

export async function downloadModelIfNeeded(
  onProgress?: (progress: number) => void
): Promise<string> {
  if (existsSync(MODEL_PATH)) {
    onProgress?.(100)
    return MODEL_PATH
  }

  if (!existsSync(MODEL_DIR)) {
    mkdirSync(MODEL_DIR, { recursive: true })
  }

  const tempPath = MODEL_PATH + '.tmp'

  // Clean up any previous partial download
  try { unlinkSync(tempPath) } catch {}

  return new Promise((resolve, reject) => {
    const doRequest = (url: string, redirectCount = 0) => {
      if (redirectCount > 10) {
        reject(new Error('Too many redirects'))
        return
      }

      const protocol = url.startsWith('https') ? https : http
      const req = protocol.get(url, { headers: { 'User-Agent': 'video-bg-remover' } }, (response) => {
        // Handle redirects
        if (
          response.statusCode &&
          response.statusCode >= 300 &&
          response.statusCode < 400 &&
          response.headers.location
        ) {
          response.resume()
          doRequest(response.headers.location, redirectCount + 1)
          return
        }

        if (response.statusCode !== 200) {
          response.resume()
          reject(new Error(`Download failed with status ${response.statusCode}`))
          return
        }

        const totalBytes = parseInt(response.headers['content-length'] || '0', 10)
        let downloadedBytes = 0
        const fileStream = createWriteStream(tempPath)

        response.on('data', (chunk: Buffer) => {
          downloadedBytes += chunk.length
          if (totalBytes > 0) {
            onProgress?.(Math.round((downloadedBytes / totalBytes) * 100))
          }
        })

        response.pipe(fileStream)

        fileStream.on('finish', () => {
          fileStream.close(() => {
            try {
              renameSync(tempPath, MODEL_PATH)
              onProgress?.(100)
              resolve(MODEL_PATH)
            } catch (err) {
              reject(err)
            }
          })
        })

        fileStream.on('error', (err: Error) => {
          try { unlinkSync(tempPath) } catch {}
          reject(err)
        })

        response.on('error', (err: Error) => {
          fileStream.destroy()
          try { unlinkSync(tempPath) } catch {}
          reject(err)
        })
      })

      req.on('error', (err) => {
        try { unlinkSync(tempPath) } catch {}
        reject(err)
      })
    }

    doRequest(MODEL_URL)
  })
}
