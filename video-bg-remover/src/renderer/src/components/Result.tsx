import { useState } from 'react'
import Preview from './Preview'

interface ResultProps {
  originalPath: string
  outputPath: string
  onSave: () => void
  onReset: () => void
}

export default function Result({ originalPath, outputPath, onSave, onReset }: ResultProps) {
  const [viewMode, setViewMode] = useState<'side-by-side' | 'result-only'>('side-by-side')

  return (
    <div className="result">
      <div className="result-controls">
        <div className="view-toggle">
          <button
            className={`btn ${viewMode === 'side-by-side' ? 'btn-active' : 'btn-ghost'}`}
            onClick={() => setViewMode('side-by-side')}
          >
            Side by Side
          </button>
          <button
            className={`btn ${viewMode === 'result-only' ? 'btn-active' : 'btn-ghost'}`}
            onClick={() => setViewMode('result-only')}
          >
            Result Only
          </button>
        </div>
        <div className="result-actions">
          <button className="btn btn-primary" onClick={onSave}>
            💾 Save Video
          </button>
          <button className="btn btn-ghost" onClick={onReset}>
            🔄 Process Another
          </button>
        </div>
      </div>

      <div className={`result-videos ${viewMode}`}>
        {viewMode === 'side-by-side' && (
          <Preview videoPath={originalPath} label="Original" />
        )}
        <Preview videoPath={outputPath} label="Background Removed" />
      </div>
    </div>
  )
}
