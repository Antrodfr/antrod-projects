import { contextBridge, ipcRenderer } from 'electron'

export type ProgressCallback = (data: { progress: number; message: string }) => void

const api = {
  openVideoDialog: (): Promise<string | null> => ipcRenderer.invoke('dialog:openVideo'),

  saveVideoDialog: (defaultName: string): Promise<string | null> =>
    ipcRenderer.invoke('dialog:saveVideo', defaultName),

  processVideo: (options: {
    inputPath: string
    backgroundType: 'transparent' | 'color'
    backgroundColor: string
  }): Promise<{ success: boolean; outputPath?: string; cancelled?: boolean; error?: string }> =>
    ipcRenderer.invoke('video:process', options),

  cancelProcessing: (): Promise<void> => ipcRenderer.invoke('video:cancel'),

  saveVideo: (sourcePath: string, destPath: string): Promise<{ success: boolean; error?: string }> =>
    ipcRenderer.invoke('video:save', { sourcePath, destPath }),

  getModelStatus: (): Promise<{ downloaded: boolean; path: string }> =>
    ipcRenderer.invoke('model:status'),

  downloadModel: (): Promise<{ success: boolean; error?: string }> =>
    ipcRenderer.invoke('model:download'),

  onProgress: (callback: ProgressCallback): (() => void) => {
    const handler = (_event: any, data: { progress: number; message: string }) => callback(data)
    ipcRenderer.on('video:progress', handler)
    return () => ipcRenderer.removeListener('video:progress', handler)
  },

  onModelDownloadProgress: (callback: (progress: number) => void): (() => void) => {
    const handler = (_event: any, progress: number) => callback(progress)
    ipcRenderer.on('model:downloadProgress', handler)
    return () => ipcRenderer.removeListener('model:downloadProgress', handler)
  }
}

contextBridge.exposeInMainWorld('api', api)

export type ElectronAPI = typeof api
