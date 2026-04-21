import { useState, useEffect } from 'react'

interface ModelSetupProps {
  onReady: () => void
}

export default function ModelSetup({ onReady }: ModelSetupProps) {
  const [status, setStatus] = useState<'checking' | 'downloading' | 'ready' | 'error'>('checking')
  const [downloadProgress, setDownloadProgress] = useState(0)
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    checkModel()
  }, [])

  const checkModel = async () => {
    const modelStatus = await window.api.getModelStatus()
    if (modelStatus.downloaded) {
      onReady()
    } else {
      setStatus('downloading')
      startDownload()
    }
  }

  const startDownload = async () => {
    const cleanup = window.api.onModelDownloadProgress((progress) => {
      setDownloadProgress(progress)
    })

    const result = await window.api.downloadModel()
    cleanup()

    if (result.success) {
      setStatus('ready')
      setTimeout(onReady, 500)
    } else {
      setStatus('error')
      setErrorMessage(result.error || 'Unknown error')
    }
  }

  const retryDownload = () => {
    setStatus('downloading')
    setDownloadProgress(0)
    setErrorMessage('')
    startDownload()
  }

  return (
    <div className="model-setup">
      {status === 'checking' && (
        <>
          <h2>⏳ Checking AI Model...</h2>
          <p>Verifying background removal model is available</p>
        </>
      )}

      {status === 'downloading' && (
        <>
          <h2>📦 Downloading AI Model</h2>
          <p>First-time setup — downloading BiRefNet-lite (~215 MB)</p>
          <p>This only happens once.</p>
          <div className="progress-bar">
            <div
              className="progress-bar-fill"
              style={{ width: `${downloadProgress}%` }}
            />
          </div>
          <p className="progress-text">{downloadProgress}%</p>
        </>
      )}

      {status === 'error' && (
        <>
          <h2>❌ Download Failed</h2>
          <p>{errorMessage}</p>
          <button className="btn btn-primary" onClick={retryDownload}>
            🔄 Retry Download
          </button>
        </>
      )}
    </div>
  )
}
