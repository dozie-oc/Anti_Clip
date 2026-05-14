import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Play, Download, Loader, CheckCircle, AlertCircle,
  Clock, Zap, FileAudio, Brain, Scissors, RotateCcw, Sparkles, Star,
  ChevronDown, ChevronUp, Mic2, FileText, Type
} from 'lucide-react'
import toast from 'react-hot-toast'
import { fetchProject, startProcessing, stopProcessing, resetProject, getClipUrl } from '@/services/api'
import { Square } from 'lucide-react'


const STAGE_STEPS = [
  { key: 'processing',    icon: FileAudio, label: 'Preparation',    desc: 'Audio & Scene Detection' },
  { key: 'transcribing', icon: Brain,     label: 'Transcription',   desc: 'Whisper AI Speech-to-Text' },
  { key: 'analyzing',    icon: Sparkles,  label: 'AI Analysis',     desc: 'Ollama Intelligence' },
  { key: 'clipping',     icon: Scissors,  label: 'Final Render',    desc: 'Generating Output' },
]

export default function ProjectDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState(null)
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [showTranscript, setShowTranscript] = useState(false)
  const pollRef = useRef(null)

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

  useEffect(() => { load() }, [id])

  useEffect(() => {
    if (project?.status === 'processing') {
      pollRef.current = setInterval(async () => {
        try {
          const data = await fetchProject(id)
          setProject(data)
          if (data.status !== 'processing') {
            clearInterval(pollRef.current)
            if (data.status === 'completed') {
              toast.success('AI Processing Complete!')
            }
          }
        } catch { /* silent */ }
      }, 2000)
    }
    return () => clearInterval(pollRef.current)
  }, [project?.status, id])

  const handleProcess = async () => {
    setProcessing(true)
    try {
      const config = {
        prompt: project.prompt,
        processing_mode: project.processing_mode,
        clip_mode: project.clip_mode,
      }
      await startProcessing(id, config)
      toast.success('Pipeline started!')
      setProject((p) => ({ ...p, status: 'processing', progress: 0, processing_stage: 'processing' }))
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
      toast.success('Ready to reprocess')
    } catch (err) {
      toast.error(err.message)
    }
  }

  const handleStop = async () => {
    if (!window.confirm('Are you sure you want to stop processing?')) return
    try {
      await stopProcessing(id)
      toast.success('Stop signal sent')
      // Immediate update to show it's stopping
      setProject((p) => ({ ...p, status: 'pending', processing_stage: null }))
    } catch (err) {
      toast.error(err.message)
    }
  }


  if (loading) return <div className="flex items-center justify-center h-64"><Loader className="text-accent animate-spin" /></div>
  if (!project) return null

  const currentStageIdx = STAGE_STEPS.findIndex((s) => s.key === project.processing_stage)

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-fade-in pb-20">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <button onClick={() => navigate('/projects')} className="text-accent-light text-sm flex items-center gap-1 hover:underline mb-2">
            <ArrowLeft size={14} /> Back
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-ink-primary">{project.name}</h1>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${(project.processing_mode === 'narration_summary' || project.processing_mode === 'narration') ? 'bg-purple-500/20 text-purple-400' : 'bg-accent/20 text-accent-light'}`}>
              {(project.processing_mode === 'narration_summary' || project.processing_mode === 'narration') ? 'Narration Recap' : 'Viral Clips'}
            </span>
          </div>
          <p className="text-ink-secondary italic">"{project.prompt}"</p>
        </div>

        <div className="flex gap-3">
          {project.status === 'pending' && (
            <button onClick={handleProcess} disabled={processing} className="btn-primary flex items-center gap-2 px-6">
              {processing ? <Loader size={18} className="animate-spin" /> : <Zap size={18} />}
              Start AI Pipeline
            </button>
          )}
          {(project.status === 'completed' || project.status === 'failed') && (
            <button onClick={handleReset} className="btn-secondary flex items-center gap-2">
              <RotateCcw size={18} /> Reprocess
            </button>
          )}
        </div>
      </div>

      {/* Progress View */}
      {project.status === 'processing' && (
        <div className="glass-card p-8 space-y-8 border-accent/20 shadow-glow">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center">
                <Loader size={20} className="text-accent animate-spin" />
              </div>
              <div>
                <h2 className="text-lg font-bold">AI is thinking...</h2>
                <p className="text-sm text-ink-secondary">Currently: {STAGE_STEPS.find(s => s.key === project.processing_stage)?.label}</p>
              </div>
            </div>
            
            <div className="flex items-center gap-6">
              <span className="text-2xl font-bold text-accent-light">{project.progress}%</span>
              <button 
                onClick={handleStop}
                className="flex items-center gap-2 text-xs font-bold text-ink-muted hover:text-red-400 transition-colors uppercase tracking-widest bg-white/5 px-3 py-1.5 rounded-lg border border-white/10"
              >
                <Square size={12} fill="currentColor" /> Stop
              </button>
            </div>
          </div>


          <div className="w-full h-3 bg-surface rounded-full overflow-hidden p-0.5 border border-white/5">
            <div className="h-full bg-gradient-accent rounded-full transition-all duration-1000" style={{ width: `${project.progress}%` }} />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {STAGE_STEPS.map((step, i) => {
              const isActive = step.key === project.processing_stage
              const isDone = currentStageIdx > i || project.status === 'completed'
              const Icon = step.icon
              return (
                <div key={step.key} className={`p-4 rounded-xl border transition-all ${isActive ? 'bg-accent/10 border-accent/40 shadow-glow' : isDone ? 'bg-success/5 border-success/30' : 'bg-surface/50 border-transparent opacity-40'}`}>
                  <Icon size={20} className={`mb-2 ${isActive ? 'text-accent-light animate-pulse' : isDone ? 'text-success' : ''}`} />
                  <p className="text-sm font-bold">{step.label}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Results View */}
      {project.status === 'completed' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {(project.processing_mode === 'narration_summary' || project.processing_mode === 'narration' || project.narration_script) ? (
              <div className="space-y-6">
                {/* Main Narration Video */}
                {project.clips && project.clips[0] && (
                  <div className="glass-card overflow-hidden shadow-glow border-purple-500/30">
                    <div className="p-4 border-b border-white/5 flex items-center justify-between bg-purple-500/5">
                      <div className="flex items-center gap-2 text-purple-400">
                        <Play size={18} fill="currentColor" />
                        <span className="font-bold uppercase tracking-widest text-xs">Final AI Recap Video</span>
                      </div>
                      <a 
                        href={project.clips[0].url || getClipUrl(id, project.clips[0].filename)} 
                        download 
                        className="btn-secondary py-1 px-3 text-xs flex items-center gap-1"
                      >
                        <Download size={14} /> Download
                      </a>
                    </div>
                    <div className="aspect-video bg-black relative">
                      <video 
                        src={project.clips[0].url || getClipUrl(id, project.clips[0].filename)} 
                        controls 
                        className="w-full h-full object-contain" 
                      />
                    </div>
                  </div>
                )}

                {/* Narration Blocks / Storyboard */}
                <div className="glass-card p-6 space-y-4">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold flex items-center gap-2">
                      <Type size={20} className="text-purple-400" /> 
                      Narration Storyboard
                    </h2>
                  </div>
                  
                  <div className="space-y-4">
                    {project.clips?.[0]?.blocks ? (
                      project.clips[0].blocks.map((block, idx) => (
                        <div key={idx} className="group flex gap-4 p-4 rounded-xl bg-white/5 border border-white/5 hover:border-purple-500/30 transition-all">
                          <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-purple-500/10 flex flex-col items-center justify-center border border-purple-500/20">
                            <span className="text-[10px] font-bold text-purple-400 uppercase">Block</span>
                            <span className="text-lg font-bold text-white">{idx + 1}</span>
                          </div>
                          <div className="flex-1 space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] font-mono bg-white/10 px-1.5 py-0.5 rounded text-ink-muted">
                                {block.scene_start.toFixed(1)}s - {block.scene_end.toFixed(1)}s
                              </span>
                            </div>
                            <p className="text-ink-primary leading-relaxed">{block.narration}</p>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="p-6 bg-black/30 rounded-xl font-serif text-lg leading-relaxed whitespace-pre-wrap text-ink-primary border border-white/5">
                        {project.narration_script || "Script not found."}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {project.clips?.map((clip, i) => (
                  <div key={clip.id} className="glass-card overflow-hidden group border-white/5 hover:border-accent/30 transition-all">
                    <div className="aspect-[9/16] bg-black relative">
                      <video src={clip.url || getClipUrl(id, clip.filename)} controls className="w-full h-full object-contain" />
                    </div>
                    <div className="p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-accent-light">Clip {i+1}</span>
                        <div className="flex gap-2">
                          {clip.score && <span className="text-xs bg-warning/20 text-warning px-2 py-0.5 rounded flex items-center gap-1"><Star size={10} fill="currentColor" /> {clip.score}</span>}
                        </div>
                      </div>
                      <p className="text-sm text-ink-secondary line-clamp-2 italic">"{clip.text}"</p>
                      <div className="flex items-center justify-between pt-2 border-t border-white/5">
                        <span className="text-[10px] text-ink-muted uppercase">{clip.duration?.toFixed(1)}s Duration</span>
                        <a href={clip.url} download className="text-accent-light hover:underline text-xs flex items-center gap-1"><Download size={12}/> Download</a>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Sidebar / Metadata */}
          <div className="space-y-6">
             <div className="glass-card p-6 space-y-4">
                <h3 className="font-bold flex items-center gap-2"><FileText size={16}/> Project Info</h3>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm"><span className="text-ink-muted">Created</span><span className="text-ink-secondary">{new Date(project.created_at).toLocaleDateString()}</span></div>
                  <div className="flex justify-between text-sm"><span className="text-ink-muted">File Size</span><span className="text-ink-secondary">{(project.file_size / (1024 * 1024)).toFixed(1)} MB</span></div>
                  <div className="flex justify-between text-sm"><span className="text-ink-muted">Provider</span><span className="text-ink-secondary">Ollama (qwen2.5)</span></div>
                </div>
             </div>

             <button 
              onClick={() => setShowTranscript(!showTranscript)}
              className="w-full glass-card p-4 flex items-center justify-between hover:bg-hover transition-all"
             >
                <span className="font-bold flex items-center gap-2"><Brain size={16}/> View Transcript</span>
                {showTranscript ? <ChevronUp size={16}/> : <ChevronDown size={16}/>}
             </button>

             {showTranscript && (
               <div className="glass-card p-4 max-h-96 overflow-y-auto space-y-3 animate-slide-up">
                 {project.transcript?.map((seg, i) => (
                   <div key={i} className="text-xs border-l-2 border-accent/30 pl-3 py-1">
                      <span className="text-ink-muted block mb-1">{seg.start.toFixed(1)}s</span>
                      <p className="text-ink-secondary">{seg.text}</p>
                   </div>
                 ))}
               </div>
             )}
          </div>
        </div>
      )}

      {/* Empty State */}
      {project.status === 'completed' && !project.clips?.length && !project.narration_script && (
        <div className="glass-card p-20 text-center space-y-4">
          <Sparkles size={48} className="mx-auto text-ink-muted" />
          <h2 className="text-2xl font-bold">No results found</h2>
          <p className="text-ink-secondary max-w-sm mx-auto">The AI couldn't find moments matching your prompt. Try reprocessing with a broader prompt.</p>
        </div>
      )}
    </div>
  )
}
