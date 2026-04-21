import { useRef, useEffect } from 'react'

interface PreviewProps {
  videoPath: string
  label: string
}

export default function Preview({ videoPath, label }: PreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.src = `file://${videoPath}`
      videoRef.current.load()
    }
  }, [videoPath])

  return (
    <div className="preview">
      <h3>{label}</h3>
      <video
        ref={videoRef}
        controls
        className="preview-video"
        playsInline
      >
        Your browser does not support the video tag.
      </video>
    </div>
  )
}
