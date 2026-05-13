import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { 
  Upload, FileVideo, X, Sparkles, Zap, Flame, 
  Heart, Laugh, MessageSquare, Monitor, Scissors, Mic2, Clock
} from 'lucide-react'
import toast from 'react-hot-toast'
import { uploadVideo } from '@/services/api'
import { useAppStore } from '@/store/appStore'

const EXAMPLE_PROMPTS = [
  { icon: Flame,          label: 'Create viral YouTube Shorts',        text: 'Find the most viral-worthy, attention-grabbing moments that would work as YouTube Shorts. Focus on shocking reveals, bold statements, and high-energy segments.' },
  { icon: Laugh,          label: 'Find funny moments',                 text: 'Identify the funniest moments — jokes, witty comebacks, awkward situations, unexpected humor, and laugh-loud dialogue.' },
  { icon: Zap,            label: 'Key insights & takeaways',           text: 'Identify the most valuable insights, actionable advice, key takeaways, and thought-provoking ideas shared in the video.' },
]

const ALLOWED = ['.mp4', '.mkv', '.mov', '.avi', '.webm']

export default function UploadPage() {
  const navigate = useNavigate()
  const { isUploading, uploadProgress, setIsUploading, setUploadProgress, resetUpload } = useAppStore()

  const [file, setFile] = useState(null)
  const [prompt, setPrompt] = useState('')
  const [processingMode, setProcessingMode] = useState('clips') // 'clips' or 'narration_summary'
  const [clipMode, setClipMode] = useState('short') // 'short' or 'long'
  const [targetDuration, setTargetDuration] = useState(5)

  const onDrop = useCallback((accepted, rejected) => {
    if (rejected.length) {
      toast.error('Unsupported file type.')
      return
    }
    if (accepted.length) {
      setFile(accepted[0])
      toast.success(`"${accepted[0].name}" ready`)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'video/*': ALLOWED },
    maxFiles: 1,
    disabled: isUploading,
  })

  const handleSubmit = async () => {
    if (!file) return toast.error('Select a video file.')
    if (processingMode === 'clips' && !prompt.trim()) return toast.error('Enter a prompt for the clips.')

    setIsUploading(true)
    setUploadProgress(0)

    try {
      const config = {
        prompt: prompt || 'Summarize the video',
        processing_mode: processingMode,
        clip_mode: clipMode,
        target_duration_minutes: targetDuration
      }
      const result = await uploadVideo(file, config, setUploadProgress)
      toast.success('Project created!')
      resetUpload()
      navigate(`/projects/${result.project_id}`)
    } catch (err) {
      toast.error(`Upload failed: ${err.message}`)
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in pb-12">
      <div>
        <h1 className="text-3xl font-bold gradient-text">New AI Project</h1>
        <p className="text-ink-secondary mt-1">Upload a video and choose your AI processing strategy.</p>
      </div>

      {/* Upload Zone */}
      <div {...getRootProps()} className={`glass-card p-10 text-center cursor-pointer transition-all border-2 border-dashed ${isDragActive ? 'border-accent bg-accent/5' : file ? 'border-success/40 bg-success/5' : 'border-border hover:border-accent/40'} ${isUploading ? 'opacity-50' : ''}`}>
        <input {...getInputProps()} />
        {file ? (
          <div className="flex items-center justify-center gap-4">
            <FileVideo size={24} className="text-success" />
            <div className="text-left">
              <p className="font-semibold text-ink-primary">{file.name}</p>
              <p className="text-sm text-ink-secondary">{(file.size / (1024 * 1024)).toFixed(1)} MB</p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <Upload size={32} className="mx-auto text-accent-light" />
            <p className="font-medium text-ink-primary">Drag & drop your video or click to browse</p>
          </div>
        )}
      </div>

      {/* Mode Selection */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button 
          onClick={() => setProcessingMode('clips')}
          className={`glass-card p-6 text-left transition-all border-2 ${processingMode === 'clips' ? 'border-accent shadow-glow' : 'border-transparent hover:bg-hover'}`}
        >
          <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center mb-4">
            <Scissors size={20} className="text-accent-light" />
          </div>
          <h3 className="font-bold text-lg mb-1">AI Viral Clips</h3>
          <p className="text-sm text-ink-secondary">Find the most engaging moments and create 9:16 vertical clips with captions.</p>
        </button>

        <button 
          onClick={() => setProcessingMode('narration_summary')}
          className={`glass-card p-6 text-left transition-all border-2 ${processingMode === 'narration_summary' ? 'border-accent shadow-glow' : 'border-transparent hover:bg-hover'}`}
        >
          <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center mb-4">
            <Mic2 size={20} className="text-purple-400" />
          </div>
          <h3 className="font-bold text-lg mb-1">Narration Summary</h3>
          <p className="text-sm text-ink-secondary">AI writes a recap script and provides a professional voice-over summary of the video.</p>
        </button>
      </div>

      {/* Config Section */}
      <div className="glass-card p-8 space-y-6">
        {processingMode === 'clips' ? (
          <>
            <div>
              <label className="font-bold block mb-2">Clip Mode</label>
              <div className="flex gap-2">
                {['short', 'long'].map(m => (
                  <button key={m} onClick={() => setClipMode(m)} className={`px-4 py-2 rounded-lg text-sm capitalize ${clipMode === m ? 'bg-accent text-white' : 'bg-surface text-ink-secondary'}`}>
                    {m} Mode
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="font-bold block mb-2">Clip Prompt</label>
              <textarea 
                value={prompt} 
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe what kind of clips to find..."
                className="input-base text-sm h-24"
              />
              <div className="flex gap-2 mt-3">
                {EXAMPLE_PROMPTS.map(({ icon: Icon, label, text }) => (
                  <button key={label} onClick={() => setPrompt(text)} className="px-3 py-1.5 rounded-md bg-surface text-xs text-ink-secondary hover:bg-hover flex items-center gap-2">
                    <Icon size={12} /> {label}
                  </button>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div>
            <label className="font-bold block mb-4 flex items-center gap-2">
              <Clock size={18} className="text-purple-400" />
              Target Summary Duration
            </label>
            <div className="flex items-center gap-4">
              <input 
                type="range" min="1" max="15" value={targetDuration} 
                onChange={(e) => setTargetDuration(e.target.value)}
                className="flex-1 accent-purple-500"
              />
              <span className="font-bold text-xl text-purple-400 w-16">{targetDuration}m</span>
            </div>
            <p className="text-sm text-ink-muted mt-2">The AI will aim for a {targetDuration} minute script based on your content.</p>
          </div>
        )}
      </div>

      <button
        onClick={handleSubmit}
        disabled={!file || isUploading}
        className="btn-primary w-full py-4 text-lg font-bold flex items-center justify-center gap-3"
      >
        {isUploading ? (
          <>
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Uploading {uploadProgress}%
          </>
        ) : (
          <>
            <Zap size={20} />
            Launch AI Pipeline
          </>
        )}
      </button>
    </div>
  )
}
