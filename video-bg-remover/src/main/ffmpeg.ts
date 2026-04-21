import ffmpeg from 'fluent-ffmpeg'
import ffmpegInstaller from '@ffmpeg-installer/ffmpeg'
import ffprobeInstaller from '@ffprobe-installer/ffprobe'
import { join } from 'path'

// In packaged app, binaries are in app.asar.unpacked
function fixAsarPath(p: string): string {
  return p.replace('app.asar', 'app.asar.unpacked')
}

const ffmpegPath = fixAsarPath(ffmpegInstaller.path)
const ffprobePath = fixAsarPath(ffprobeInstaller.path)
console.log('[ffmpeg] ffmpeg path:', ffmpegPath)
console.log('[ffmpeg] ffprobe path:', ffprobePath)

ffmpeg.setFfmpegPath(ffmpegPath)
ffmpeg.setFfprobePath(ffprobePath)

export interface VideoInfo {
  fps: number
  width: number
  height: number
  duration: number
}

export function getVideoInfo(inputPath: string): Promise<VideoInfo> {
  return new Promise((resolve, reject) => {
    ffmpeg.ffprobe(inputPath, (err, data) => {
      if (err) {
        reject(err)
        return
      }
      const videoStream = data.streams.find((s) => s.codec_type === 'video')
      if (!videoStream) {
        reject(new Error('No video stream found'))
        return
      }

      let fps = 30
      if (videoStream.r_frame_rate) {
        const parts = videoStream.r_frame_rate.split('/')
        fps = parseInt(parts[0]) / parseInt(parts[1] || '1')
      }

      const info = {
        fps: Math.round(fps * 100) / 100,
        width: videoStream.width || 1920,
        height: videoStream.height || 1080,
        duration: parseFloat(data.format.duration as any) || 0
      }
      console.log('[ffmpeg] Video info:', JSON.stringify(info))
      resolve(info)
    })
  })
}

export function extractFrames(inputPath: string, outputDir: string): Promise<void> {
  return new Promise((resolve, reject) => {
    let stderrOutput = ''
    ffmpeg(inputPath)
      .output(join(outputDir, 'frame-%06d.png'))
      .on('stderr', (line: string) => {
        stderrOutput += line + '\n'
      })
      .on('end', () => {
        console.log('[ffmpeg] Frame extraction complete')
        resolve()
      })
      .on('error', (err) => {
        console.error('[ffmpeg] Frame extraction failed:', stderrOutput.slice(-1000))
        reject(new Error(`Frame extraction failed: ${err.message}\n${stderrOutput.slice(-500)}`))
      })
      .run()
  })
}

export function extractAudio(inputPath: string, outputPath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    let stderrOutput = ''
    ffmpeg(inputPath)
      .output(outputPath)
      .noVideo()
      .audioCodec('aac')
      .on('stderr', (line: string) => {
        stderrOutput += line + '\n'
      })
      .on('end', () => {
        console.log('[ffmpeg] Audio extraction complete')
        resolve()
      })
      .on('error', (err) => {
        console.error('[ffmpeg] Audio extraction failed:', stderrOutput.slice(-500))
        reject(new Error(`Audio extraction failed: ${err.message}`))
      })
      .run()
  })
}

export function assembleVideo(
  framesDir: string,
  audioPath: string | null,
  outputPath: string,
  fps: number,
  transparent: boolean
): Promise<void> {
  return new Promise((resolve, reject) => {
    let stderrOutput = ''
    let cmd = ffmpeg()
      .input(join(framesDir, 'frame-%06d.png'))
      .inputFPS(fps)

    if (audioPath) {
      cmd = cmd.input(audioPath)
    }

    if (transparent) {
      // WebM VP9 with alpha
      cmd = cmd
        .outputOptions([
          '-c:v', 'libvpx-vp9',
          '-pix_fmt', 'yuva420p',
          '-auto-alt-ref', '0',
          '-b:v', '2M',
          '-crf', '30'
        ])
    } else {
      // MP4 H.264
      cmd = cmd
        .outputOptions([
          '-c:v', 'libx264',
          '-pix_fmt', 'yuv420p',
          '-crf', '23',
          '-preset', 'medium'
        ])
    }

    if (audioPath) {
      if (transparent) {
        // WebM only supports Vorbis or Opus audio
        cmd = cmd.outputOptions(['-c:a', 'libopus', '-b:a', '128k', '-shortest'])
      } else {
        cmd = cmd.outputOptions(['-c:a', 'aac', '-b:a', '128k', '-shortest'])
      }
    }

    cmd
      .outputOptions(['-y'])
      .output(outputPath)
      .on('stderr', (line: string) => {
        stderrOutput += line + '\n'
      })
      .on('end', () => {
        console.log('[ffmpeg] Video assembly complete')
        resolve()
      })
      .on('error', (err) => {
        console.error('[ffmpeg] Video assembly failed:', stderrOutput.slice(-1000))
        reject(new Error(`Video assembly failed: ${err.message}\n${stderrOutput.slice(-500)}`))
      })
      .run()
  })
}
