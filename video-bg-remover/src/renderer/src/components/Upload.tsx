import { useState, useCallback } from 'react'

interface UploadProps {
  onVideoSelected: (path: string) => void
}

export default function Upload({ onVideoSelected }: UploadProps) {
  const [isDragging, setIsDragging] = useState(false)

  const handleClick = async () => {
    const path = await window.api.openVideoDialog()
    if (path) onVideoSelected(path)
  }

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(false)

      const files = e.dataTransfer.files
      if (files.length > 0) {
        const file = files[0]
        const videoExtensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv', '.flv']
        const ext = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
        if (videoExtensions.includes(ext)) {
          onVideoSelected(file.path)
        } else {
          alert('Please select a valid video file (MP4, MOV, AVI, MKV, WebM, WMV, FLV)')
        }
      }
    },
    [onVideoSelected]
  )

  return (
    <div
      className={`upload-zone ${isDragging ? 'upload-zone--dragging' : ''}`}
      onClick={handleClick}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="upload-icon">📁</div>
      <h2>Upload a Video</h2>
      <p>Drag and drop a video file here, or click to browse</p>
      <p className="upload-formats">
        Supported: MP4, MOV, AVI, MKV, WebM, WMV, FLV
      </p>
    </div>
  )
}
