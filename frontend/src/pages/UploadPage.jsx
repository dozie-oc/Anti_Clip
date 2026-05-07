import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { Upload, FileVideo, X, Sparkles, Zap, Flame, Heart, Laugh, MessageSquare } from 'lucide-react'
import toast from 'react-hot-toast'
import { uploadVideo } from '@/services/api'
import { useAppStore } from '@/store/appStore'

const EXAMPLE_PROMPTS = [
  { icon: Flame,          label: 'Create viral YouTube Shorts',        text: 'Find the most viral-worthy, attention-grabbing moments that would work as YouTube Shorts. Focus on shocking reveals, bold statements, and high-energy segments.' },
  { icon: Laugh,          label: 'Find funny moments',                 text: 'Identify the funniest moments — jokes, witty comebacks, awkward situations, unexpected humor, and laugh-out-loud dialogue.' },
  { icon: Heart,          label: 'Extract emotional dialogue',         text: 'Find emotionally impactful moments — heartfelt conversations, inspiring speeches, vulnerable admissions, and deeply moving exchanges.' },
  { icon: MessageSquare,  label: 'Clip sarcastic conversations',       text: 'Extract the most sarcastic, sharp-witted, and passive-aggressive exchanges. Focus on clever comebacks and ironic observations.' },
  { icon: Zap,            label: 'Key insights & takeaways',           text: 'Identify the most valuable insights, actionable advice, key takeaways, and thought-provoking ideas shared in the video.' },
  { icon: Sparkles,       label: 'Most engaging moments',              text: 'Find the most engaging and captivating segments — dramatic tension, surprising twists, compelling arguments, and peak-interest moments.' },
]

const ALLOWED = ['.mp4', '.mkv', '.mov', '.avi', '.webm']

export default function UploadPage() {
  const navigate = useNavigate()
  const { isUploading, uploadProgress, setIsUploading, setUploadProgress, resetUpload, addProject } = useAppStore()

  const [file, setFile] = useState(null)
  const [prompt, setPrompt] = useState('')

  // ── Dropzone ────────────────────────────────────────────────────────────
  const onDrop = useCallback((accepted, rejected) => {
    if (rejected.length) {
      toast.error('Unsupported file type. Use MP4, MKV, MOV, AVI, or WebM.')
      return
    }
    if (accepted.length) {
      setFile(accepted[0])
      toast.success(`"${accepted[0].name}" ready to upload`)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'video/*': ALLOWED },
    maxFiles: 1,
    disabled: isUploading,
  })

  // ── Upload + Create ────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!file) {
      toast.error('Please select a video file first.')
      return
    }
    if (!prompt.trim()) {
      toast.error('Please enter a prompt describing what clips to create.')
      return
    }

    setIsUploading(true)
    setUploadProgress(0)

    try {
      const result = await uploadVideo(file, prompt, setUploadProgress)
      toast.success('Video uploaded — project created!')
      resetUpload()
      setFile(null)
      setPrompt('')
      navigate(`/projects/${result.project_id}`)
    } catch (err) {
      toast.error(`Upload failed: ${err.message}`)
    } finally {
      setIsUploading(false)
    }
  }

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold gradient-text">Upload Video</h1>
        <p className="text-ink-secondary mt-1">
          Drop your video and describe the clips you want — AI handles the rest.
        </p>
      </div>

      {/* Upload Zone */}
      <div
        {...getRootProps()}
        className={`
          glass-card p-10 text-center cursor-pointer transition-all duration-300
          border-2 border-dashed
          ${isDragActive
            ? 'border-accent bg-accent/5 scale-[1.01] shadow-glow'
            : file
              ? 'border-success/40 bg-success/5'
              : 'border-border hover:border-accent/40 hover:bg-hover/50'
          }
          ${isUploading ? 'pointer-events-none opacity-60' : ''}
        `}
      >
        <input {...getInputProps()} />

        {file ? (
          <div className="flex items-center justify-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-success/15 flex items-center justify-center">
              <FileVideo size={24} className="text-success" />
            </div>
            <div className="text-left">
              <p className="font-semibold text-ink-primary">{file.name}</p>
              <p className="text-sm text-ink-secondary">{formatSize(file.size)}</p>
            </div>
            {!isUploading && (
              <button
                onClick={(e) => { e.stopPropagation(); setFile(null) }}
                className="ml-4 p-2 rounded-lg hover:bg-hover text-ink-muted hover:text-danger transition-colors"
              >
                <X size={18} />
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center mx-auto">
              <Upload size={28} className={`${isDragActive ? 'text-accent animate-bounce' : 'text-accent-light'}`} />
            </div>
            <div>
              <p className="font-semibold text-ink-primary text-lg">
                {isDragActive ? 'Drop your video here' : 'Drag & drop your video'}
              </p>
              <p className="text-sm text-ink-secondary mt-1">
                or click to browse • MP4, MKV, MOV, AVI, WebM • Up to 2GB
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Upload progress bar */}
      {isUploading && (
        <div className="glass-card p-4 animate-slide-up">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-ink-secondary">Uploading...</span>
            <span className="font-semibold text-accent-light">{uploadProgress}%</span>
          </div>
          <div className="w-full h-2 bg-surface rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-accent rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Prompt Input */}
      <div className="glass-card p-6 space-y-4">
        <div>
          <label className="section-title flex items-center gap-2" htmlFor="prompt-input">
            <Sparkles size={18} className="text-accent-light" />
            Clip Prompt
          </label>
          <p className="section-sub mt-1">
            Describe what kind of clips you want the AI to create
          </p>
        </div>

        <textarea
          id="prompt-input"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g., Find the funniest moments and create viral YouTube Shorts..."
          rows={4}
          className="input-base resize-none text-sm"
          disabled={isUploading}
        />

        {/* Example prompts */}
        <div>
          <p className="text-xs text-ink-muted mb-2 uppercase tracking-wider font-semibold">
            Quick prompts
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {EXAMPLE_PROMPTS.map(({ icon: Icon, label, text }) => (
              <button
                key={label}
                onClick={() => setPrompt(text)}
                disabled={isUploading}
                className={`
                  flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs font-medium text-left
                  transition-all duration-150
                  ${prompt === text
                    ? 'bg-accent/15 text-accent-light border border-accent/30'
                    : 'bg-surface text-ink-secondary hover:text-ink-primary hover:bg-hover border border-transparent'
                  }
                `}
              >
                <Icon size={14} className="shrink-0" />
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!file || !prompt.trim() || isUploading}
        className="btn-primary w-full text-center py-3.5 text-base flex items-center justify-center gap-2"
      >
        {isUploading ? (
          <>
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Uploading...
          </>
        ) : (
          <>
            <Zap size={18} />
            Upload & Create Project
          </>
        )}
      </button>
    </div>
  )
}
