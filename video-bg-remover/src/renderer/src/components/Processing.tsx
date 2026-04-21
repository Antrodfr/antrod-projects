interface ProcessingProps {
  progress: number
  message: string
  onCancel: () => void
}

export default function Processing({ progress, message, onCancel }: ProcessingProps) {
  return (
    <div className="processing">
      <h2>🔄 Processing Video</h2>
      <p className="processing-message">{message}</p>
      <div className="progress-bar">
        <div
          className="progress-bar-fill"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="progress-text">{progress}%</p>
      <button className="btn btn-danger" onClick={onCancel}>
        ✕ Cancel
      </button>
    </div>
  )
}
