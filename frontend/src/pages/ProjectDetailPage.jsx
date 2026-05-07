import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Play, Download, Loader, CheckCircle, AlertCircle,
  Clock, Zap, FileAudio, Brain, Scissors, RotateCcw, Sparkles, Star,
  ChevronDown, ChevronUp
} from 'lucide-react'
import toast from 'react-hot-toast'
import { fetchProject, startProcessing, resetProject, getClipUrl } from '@/services/api'

const STAGE_STEPS = [
  { key: 'audio_extraction', icon: FileAudio,  label: 'Audio Extraction',  desc: 'Extracting audio track via FFmpeg' },
  { key: 'transcription',    icon: Brain,       label: 'Transcription',     desc: 'Transcribing speech with Whisper AI' },
  { key: 'llm_analysis',     icon: Sparkles,    label: 'AI Analysis',       desc: 'Scoring segments with LLM' },
  { key: 'clip_generation',  icon: Scissors,    label: 'Clip Generation',   desc: 'Cutting top clips via FFmpeg' },
]

export default function ProjectDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState(null)
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [showTranscript, setShowTranscript] = useState(false)
  const pollRef = useRef(null)

  // ── Fetch project ──────────────────────────────────────────────────────
  const load = async () => {
    try {
      const data = await fetchProject(id)
      setProject(data)
    } catch (err) {
      toast.error('Project not found')
      navigate('/projects')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id]) // eslint-disable-line

  // Poll while processing
  useEffect(() => {
    if (project?.status === 'processing') {
      pollRef.current = setInterval(async () => {
        try {
          const data = await fetchProject(id)
          setProject(data)
          if (data.status !== 'processing') {
            clearInterval(pollRef.current)
            if (data.status === 'completed') {
              toast.success(`Done! ${data.clips?.length || 0} clips generated.`)
            }
          }
        } catch { /* silent */ }
      }, 2000)
    }
    return () => clearInterval(pollRef.current)
  }, [project?.status, id])

  // ── Start processing ──────────────────────────────────────────────────
  const handleProcess = async () => {
    setProcessing(true)
    try {
      await startProcessing(id)
      toast.success('Processing started!')
      setProject((p) => ({ ...p, status: 'processing', progress: 0, processing_stage: 'queued' }))
    } catch (err) {
      toast.error(err.message)
    } finally {
      setProcessing(false)
    }
  }

  const handleReset = async () => {
    try {
      const data = await resetProject(id)
      setProject(data)
      toast.success('Project reset — ready to reprocess')
    } catch (err) {
      toast.error(err.message)
    }
  }

  // ── Loading state ─────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader size={32} className="text-accent animate-spin" />
      </div>
    )
  }

  if (!project) return null

  const currentStageIdx = STAGE_STEPS.findIndex((s) => s.key === project.processing_stage)

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back + Header */}
      <button
        onClick={() => navigate('/projects')}
        className="btn-ghost flex items-center gap-1.5 -ml-3 text-sm"
      >
        <ArrowLeft size={16} /> Back to Projects
      </button>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink-primary">
            {project.name || project.original_filename}
          </h1>
          <p className="text-ink-secondary text-sm mt-1 max-w-lg">
            "{project.prompt}"
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2 shrink-0">
          {project.status === 'pending' && (
            <button
              onClick={handleProcess}
              disabled={processing}
              className="btn-primary flex items-center gap-2"
            >
              {processing ? (
                <Loader size={16} className="animate-spin" />
              ) : (
                <Zap size={16} />
              )}
              Start Processing
            </button>
          )}
          {(project.status === 'completed' || project.status === 'failed') && (
            <button onClick={handleReset} className="btn-secondary flex items-center gap-2">
              <RotateCcw size={16} />
              Reprocess
            </button>
          )}
        </div>
      </div>

      {/* Processing pipeline stages */}
      {project.status === 'processing' && (
        <div className="glass-card p-6 animate-slide-up">
          <h2 className="section-title mb-4 flex items-center gap-2">
            <Loader size={18} className="text-accent animate-spin" />
            Processing Pipeline
          </h2>

          {/* Progress bar */}
          <div className="mb-6">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-ink-secondary">Overall progress</span>
              <span className="font-semibold text-accent-light">{project.progress}%</span>
            </div>
            <div className="w-full h-2.5 bg-surface rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-accent rounded-full transition-all duration-700 ease-out"
                style={{ width: `${project.progress}%` }}
              />
            </div>
          </div>

          {/* Stage indicators */}
          <div className="grid grid-cols-4 gap-3">
            {STAGE_STEPS.map((step, i) => {
              const isActive = step.key === project.processing_stage
              const isDone = currentStageIdx > i || project.status === 'completed'
              const Icon = step.icon

              return (
                <div
                  key={step.key}
                  className={`
                    p-3 rounded-lg text-center transition-all duration-300
                    ${isActive ? 'bg-accent/15 border border-accent/30 scale-[1.02]' : ''}
                    ${isDone ? 'bg-success/10 border border-success/20' : ''}
                    ${!isActive && !isDone ? 'bg-surface/50 border border-transparent' : ''}
                  `}
                >
                  <div className="flex justify-center mb-2">
                    {isDone ? (
                      <CheckCircle size={20} className="text-success" />
                    ) : isActive ? (
                      <Icon size={20} className="text-accent-light animate-pulse" />
                    ) : (
                      <Icon size={20} className="text-ink-muted" />
                    )}
                  </div>
                  <p className={`text-xs font-semibold ${isActive ? 'text-accent-light' : isDone ? 'text-success' : 'text-ink-muted'}`}>
                    {step.label}
                  </p>
                  <p className="text-[10px] text-ink-muted mt-0.5">{step.desc}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Error state */}
      {project.status === 'failed' && project.error_message && (
        <div className="glass-card p-5 border-danger/30 bg-danger/5 animate-slide-up">
          <div className="flex items-start gap-3">
            <AlertCircle size={20} className="text-danger shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-danger">Processing Failed</h3>
              <p className="text-sm text-ink-secondary mt-1">{project.error_message}</p>
            </div>
          </div>
        </div>
      )}

      {/* Completed — clip results */}
      {project.status === 'completed' && project.clips?.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="section-title flex items-center gap-2">
              <Scissors size={18} className="text-accent-light" />
              Generated Clips ({project.clips.length})
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {project.clips.map((clip, i) => (
              <div key={clip.id} className="glass-card overflow-hidden group">
                {/* Video player */}
                <div className="relative bg-black aspect-video">
                  <video
                    controls
                    preload="metadata"
                    className="w-full h-full object-contain"
                    src={clip.url || getClipUrl(id, clip.filename)}
                  >
                    Your browser does not support video playback.
                  </video>
                </div>

                {/* Clip info */}
                <div className="p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-ink-primary text-sm">
                      Clip {i + 1}
                    </h3>
                    <div className="flex items-center gap-2">
                      {clip.score && (
                        <span className="flex items-center gap-1 text-xs font-semibold text-warning">
                          <Star size={12} fill="currentColor" />
                          {clip.score}/10
                        </span>
                      )}
                      <span className="text-xs text-ink-muted">
                        {clip.duration?.toFixed(1)}s
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-ink-secondary line-clamp-2">
                    {clip.text}
                  </p>

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[10px] text-ink-muted">
                      {clip.start?.toFixed(1)}s — {clip.end?.toFixed(1)}s
                    </span>
                    <a
                      href={clip.url || getClipUrl(id, clip.filename)}
                      download={clip.filename}
                      className="btn-ghost flex items-center gap-1 text-xs py-1.5 px-2.5 text-accent-light"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Download size={13} />
                      Download
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Completed with no clips */}
      {project.status === 'completed' && (!project.clips || project.clips.length === 0) && (
        <div className="glass-card p-12 text-center">
          <Scissors size={32} className="text-ink-muted mx-auto mb-3" />
          <h3 className="font-semibold text-ink-primary">No clips generated</h3>
          <p className="text-sm text-ink-secondary mt-1">
            Try adjusting your prompt or lowering the score threshold
          </p>
        </div>
      )}

      {/* Transcript (collapsible) */}
      {project.transcript && project.transcript.length > 0 && (
        <div className="glass-card overflow-hidden">
          <button
            onClick={() => setShowTranscript(!showTranscript)}
            className="w-full px-5 py-4 flex items-center justify-between hover:bg-hover/50 transition-colors"
          >
            <span className="section-title flex items-center gap-2">
              <Brain size={18} className="text-accent-light" />
              Transcript ({project.transcript.length} segments)
            </span>
            {showTranscript ? <ChevronUp size={18} className="text-ink-muted" /> : <ChevronDown size={18} className="text-ink-muted" />}
          </button>

          {showTranscript && (
            <div className="px-5 pb-5 space-y-2 max-h-96 overflow-y-auto border-t border-border">
              {project.transcript.map((seg, i) => (
                <div key={i} className="flex gap-3 py-2 border-b border-border/50 last:border-0">
                  <span className="text-[10px] text-ink-muted font-mono shrink-0 w-24 pt-0.5">
                    {seg.start?.toFixed(1)}s – {seg.end?.toFixed(1)}s
                  </span>
                  <p className="text-sm text-ink-secondary">{seg.text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Pending state CTA */}
      {project.status === 'pending' && (
        <div className="glass-card p-12 text-center animate-slide-up">
          <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center mx-auto mb-4">
            <Zap size={28} className="text-accent-light" />
          </div>
          <h3 className="text-lg font-semibold text-ink-primary mb-1">Ready to Process</h3>
          <p className="text-ink-secondary text-sm mb-6 max-w-sm mx-auto">
            Your video is uploaded. Click below to start the AI clipping pipeline.
          </p>
          <button
            onClick={handleProcess}
            disabled={processing}
            className="btn-primary flex items-center gap-2 mx-auto"
          >
            {processing ? <Loader size={16} className="animate-spin" /> : <Zap size={16} />}
            Start Processing
          </button>
        </div>
      )}
    </div>
  )
}
