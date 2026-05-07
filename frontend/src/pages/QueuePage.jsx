import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ListVideo, Loader, CheckCircle, AlertCircle, Clock,
  FileAudio, Brain, Sparkles, Scissors
} from 'lucide-react'
import { fetchProjects } from '@/services/api'
import toast from 'react-hot-toast'

const STAGE_ICONS = {
  queued:           Clock,
  audio_extraction: FileAudio,
  transcription:    Brain,
  llm_analysis:     Sparkles,
  clip_generation:  Scissors,
  completed:        CheckCircle,
}

export default function QueuePage() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const pollRef = useRef(null)

  const load = async () => {
    try {
      const data = await fetchProjects()
      setProjects(data)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  // Poll for updates
  useEffect(() => {
    pollRef.current = setInterval(load, 3000)
    return () => clearInterval(pollRef.current)
  }, [])

  const processingJobs = projects.filter((p) => p.status === 'processing')
  const recentCompleted = projects.filter((p) => p.status === 'completed').slice(0, 5)
  const recentFailed = projects.filter((p) => p.status === 'failed').slice(0, 3)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader size={32} className="text-accent animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold gradient-text">Processing Queue</h1>
        <p className="text-ink-secondary mt-1">
          Monitor active jobs and recent results
        </p>
      </div>

      {/* Active Jobs */}
      <div className="space-y-3">
        <h2 className="section-title flex items-center gap-2">
          <Loader size={16} className={processingJobs.length ? 'text-accent animate-spin' : 'text-ink-muted'} />
          Active Jobs ({processingJobs.length})
        </h2>

        {processingJobs.length === 0 ? (
          <div className="glass-card p-10 text-center">
            <ListVideo size={28} className="text-ink-muted mx-auto mb-2" />
            <p className="text-ink-secondary text-sm">No jobs currently running</p>
          </div>
        ) : (
          processingJobs.map((project) => {
            const StageIcon = STAGE_ICONS[project.processing_stage] || Clock
            return (
              <div
                key={project.id}
                onClick={() => navigate(`/projects/${project.id}`)}
                className="glass-card p-5 cursor-pointer hover:border-accent/30 transition-all duration-200"
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-ink-primary">
                    {project.name || project.original_filename}
                  </h3>
                  <div className="flex items-center gap-2 text-sm text-accent-light">
                    <StageIcon size={14} className="animate-pulse" />
                    <span className="capitalize">
                      {project.processing_stage?.replace('_', ' ') || 'starting'}
                    </span>
                  </div>
                </div>

                <div className="w-full h-2 bg-surface rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-accent rounded-full transition-all duration-700"
                    style={{ width: `${project.progress}%` }}
                  />
                </div>
                <div className="flex justify-between mt-1.5">
                  <span className="text-xs text-ink-muted truncate max-w-xs">
                    {project.prompt}
                  </span>
                  <span className="text-xs font-semibold text-accent-light">
                    {project.progress}%
                  </span>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Recent completed */}
      {recentCompleted.length > 0 && (
        <div className="space-y-3">
          <h2 className="section-title flex items-center gap-2">
            <CheckCircle size={16} className="text-success" />
            Recently Completed
          </h2>

          {recentCompleted.map((p) => (
            <div
              key={p.id}
              onClick={() => navigate(`/projects/${p.id}`)}
              className="glass-card p-4 flex items-center gap-3 cursor-pointer hover:bg-hover/50 transition-colors"
            >
              <CheckCircle size={16} className="text-success shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-ink-primary text-sm truncate">
                  {p.name || p.original_filename}
                </p>
                <p className="text-xs text-ink-muted">{p.clips?.length || 0} clips</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Recent failed */}
      {recentFailed.length > 0 && (
        <div className="space-y-3">
          <h2 className="section-title flex items-center gap-2">
            <AlertCircle size={16} className="text-danger" />
            Failed
          </h2>

          {recentFailed.map((p) => (
            <div
              key={p.id}
              onClick={() => navigate(`/projects/${p.id}`)}
              className="glass-card p-4 flex items-center gap-3 cursor-pointer hover:bg-hover/50 transition-colors"
            >
              <AlertCircle size={16} className="text-danger shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-ink-primary text-sm truncate">
                  {p.name || p.original_filename}
                </p>
                <p className="text-xs text-danger truncate">{p.error_message || 'Unknown error'}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
