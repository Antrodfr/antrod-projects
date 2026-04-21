import { useState, useEffect } from 'react'
import Upload from './components/Upload'
import Preview from './components/Preview'
import BackgroundSelector from './components/BackgroundSelector'
import Processing from './components/Processing'
import Result from './components/Result'
import ModelSetup from './components/ModelSetup'

type AppState = 'setup' | 'upload' | 'preview' | 'processing' | 'result'

export default function App() {
  const [state, setState] = useState<AppState>('setup')
  const [inputPath, setInputPath] = useState<string | null>(null)
  const [outputPath, setOutputPath] = useState<string | null>(null)
  const [backgroundType, setBackgroundType] = useState<'transparent' | 'color'>('transparent')
  const [backgroundColor, setBackgroundColor] = useState('#00ff00')
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState('')

  useEffect(() => {
    window.api.getModelStatus().then((status) => {
      if (status.downloaded) {
        setState('upload')
      }
    })
  }, [])

  const handleModelReady = () => {
    setState('upload')
  }

  const handleVideoSelected = (path: string) => {
    setInputPath(path)
    setState('preview')
  }

  const handleStartProcessing = async () => {
    if (!inputPath) return
    setState('processing')
    setProgress(0)
    setProgressMessage('Starting...')

    const cleanup = window.api.onProgress(({ progress, message }) => {
      setProgress(progress)
      setProgressMessage(message)
    })

    const result = await window.api.processVideo({
      inputPath,
      backgroundType,
      backgroundColor
    })

    cleanup()

    if (result.success && result.outputPath) {
      setOutputPath(result.outputPath)
      setState('result')
    } else if (result.cancelled) {
      setState('preview')
    } else {
      alert(`Processing failed: ${result.error}`)
      setState('preview')
    }
  }

  const handleCancel = async () => {
    await window.api.cancelProcessing()
    setState('preview')
  }

  const handleSave = async () => {
    if (!outputPath) return
    const ext = backgroundType === 'transparent' ? 'webm' : 'mp4'
    const destPath = await window.api.saveVideoDialog(`output.${ext}`)
    if (destPath) {
      const result = await window.api.saveVideo(outputPath, destPath)
      if (result.success) {
        alert('Video saved successfully!')
      } else {
        alert(`Failed to save: ${result.error}`)
      }
    }
  }

  const handleReset = () => {
    setInputPath(null)
    setOutputPath(null)
    setProgress(0)
    setProgressMessage('')
    setState('upload')
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎬 Video Background Remover</h1>
        {state !== 'setup' && state !== 'upload' && (
          <button className="btn btn-ghost" onClick={handleReset}>
            ← New Video
          </button>
        )}
      </header>

      <main className="app-content">
        {state === 'setup' && <ModelSetup onReady={handleModelReady} />}

        {state === 'upload' && <Upload onVideoSelected={handleVideoSelected} />}

        {state === 'preview' && inputPath && (
          <div className="preview-container">
            <Preview videoPath={inputPath} label="Original Video" />
            <BackgroundSelector
              backgroundType={backgroundType}
              backgroundColor={backgroundColor}
              onTypeChange={setBackgroundType}
              onColorChange={setBackgroundColor}
            />
            <button className="btn btn-primary btn-large" onClick={handleStartProcessing}>
              🚀 Remove Background
            </button>
          </div>
        )}

        {state === 'processing' && (
          <Processing
            progress={progress}
            message={progressMessage}
            onCancel={handleCancel}
          />
        )}

        {state === 'result' && inputPath && outputPath && (
          <Result
            originalPath={inputPath}
            outputPath={outputPath}
            onSave={handleSave}
            onReset={handleReset}
          />
        )}
      </main>
    </div>
  )
}
