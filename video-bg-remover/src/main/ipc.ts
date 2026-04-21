import { ipcMain, dialog, BrowserWindow } from 'electron'
import { processVideo, cancelProcessing } from './processing'
import { downloadModelIfNeeded, getModelStatus, cleanupOldModels } from './model-download'
import { join } from 'path'
import { writeFile, copyFile } from 'fs/promises'

export function registerIpcHandlers(): void {
  // Clean up old model files on startup
  cleanupOldModels()

  ipcMain.handle('dialog:openVideo', async () => {
    const result = await dialog.showOpenDialog({
      properties: ['openFile'],
      filters: [
        {
          name: 'Video Files',
          extensions: ['mp4', 'mov', 'avi', 'mkv', 'webm', 'wmv', 'flv']
        }
      ]
    })
    if (result.canceled || result.filePaths.length === 0) return null
    return result.filePaths[0]
  })

  ipcMain.handle('dialog:saveVideo', async (_event, defaultName: string) => {
    const result = await dialog.showSaveDialog({
      defaultPath: defaultName,
      filters: [
        { name: 'WebM Video (transparent)', extensions: ['webm'] },
        { name: 'MP4 Video', extensions: ['mp4'] }
      ]
    })
    if (result.canceled || !result.filePath) return null
    return result.filePath
  })

  ipcMain.handle(
    'video:process',
    async (
      event,
      {
        inputPath,
        backgroundType,
        backgroundColor
      }: {
        inputPath: string
        backgroundType: 'transparent' | 'color'
        backgroundColor: string
      }
    ) => {
      const win = BrowserWindow.fromWebContents(event.sender)
      const onProgress = (progress: number, message: string) => {
        win?.webContents.send('video:progress', { progress, message })
      }
      try {
        const outputPath = await processVideo(
          inputPath,
          backgroundType,
          backgroundColor,
          onProgress
        )
        return { success: true, outputPath }
      } catch (error: any) {
        if (error.message === 'CANCELLED') {
          return { success: false, cancelled: true }
        }
        return { success: false, error: error.message }
      }
    }
  )

  ipcMain.handle('video:cancel', async () => {
    cancelProcessing()
  })

  ipcMain.handle('video:save', async (_event, { sourcePath, destPath }: { sourcePath: string; destPath: string }) => {
    try {
      await copyFile(sourcePath, destPath)
      return { success: true }
    } catch (error: any) {
      return { success: false, error: error.message }
    }
  })

  ipcMain.handle('model:status', async () => {
    return getModelStatus()
  })

  ipcMain.handle('model:download', async (event) => {
    const win = BrowserWindow.fromWebContents(event.sender)
    const onProgress = (progress: number) => {
      win?.webContents.send('model:downloadProgress', progress)
    }
    try {
      await downloadModelIfNeeded(onProgress)
      return { success: true }
    } catch (error: any) {
      return { success: false, error: error.message }
    }
  })
}
