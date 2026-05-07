import { useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FolderOpen, Trash2, Play, Clock, CheckCircle, AlertCircle,
  Loader, FileVideo, Sparkles
} from 'lucide-react'
import toast from 'react-hot-toast'
import { fetchProjects, deleteProject } from '@/services/api'
import { useAppStore } from '@/store/appStore'

const STATUS_CONFIG = {
  pending:    { badge: 'badge-pending',    icon: Clock,       label: 'Pending' },
  processing: { badge: 'badge-processing', icon: Loader,      label: 'Processing' },
  completed:  { badge: 'badge-completed',  icon: CheckCircle, label: 'Completed' },
  failed:     { badge: 'badge-failed',     icon: AlertCircle, label: 'Failed' },
}

export default function ProjectsPage() {
  const navigate = useNavigate()
  const { projects, setProjects, projectsLoading, setProjectsLoading, removeProject } = useAppStore()
  const pollRef = useRef(null)

  const load = useCallback(async () => {
    setProjectsLoading(true)
    try {
      const data = await fetchProjects()
      setProjects(data)
    } catch (err) {
      toast.error(`Failed to load projects: ${err.message}`)
    } finally {
      setProjectsLoading(false)
    }
  }, [setProjects, setProjectsLoading])

  // Initial load
  useEffect(() => { load() }, []) // eslint-disable-line

  // Poll every 3s for processing updates
  useEffect(() => {
    pollRef.current = setInterval(async () => {
      const hasProcessing = projects.some((p) => p.status === 'processing')
      if (hasProcessing) {
        try {
          const data = await fetchProjects()
          setProjects(data)
        } catch { /* silent */ }
      }
    }, 3000)
    return () => clearInterval(pollRef.current)
  }, [projects, setProjects])

  const handleDelete = async (e, id) => {
    e.stopPropagation()
    if (!window.confirm('Delete this project and all its clips?')) return
    try {
      await deleteProject(id)
      removeProject(id)
      toast.success('Project deleted')
    } catch (err) {
      toast.error(err.message)
    }
  }

  const formatDate = (d) => {
    const date = new Date(d)
    return date.toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  }

  const formatSize = (bytes) => {
    if (!bytes) return ''
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold gradient-text">Projects</h1>
          <p className="text-ink-secondary mt-1">
            {projects.length} project{projects.length !== 1 ? 's' : ''} total
          </p>
        </div>
        <button
          onClick={() => navigate('/upload')}
          className="btn-primary flex items-center gap-2"
        >
          <Sparkles size={16} />
          New Project
        </button>
      </div>

      {/* Loading */}
      {projectsLoading && !projects.length && (
        <div className="glass-card p-16 text-center">
          <Loader size={32} className="text-accent animate-spin mx-auto mb-3" />
          <p className="text-ink-secondary">Loading projects...</p>
        </div>
      )}

      {/* Empty state */}
      {!projectsLoading && !projects.length && (
        <div className="glass-card p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center mx-auto mb-4">
            <FolderOpen size={28} className="text-accent-light" />
          </div>
          <h3 className="text-lg font-semibold text-ink-primary mb-1">No projects yet</h3>
          <p className="text-ink-secondary mb-6">
            Upload a video and let AI create clips for you
          </p>
          <button onClick={() => navigate('/upload')} className="btn-primary">
            Upload Your First Video
          </button>
        </div>
      )}

      {/* Project list */}
      <div className="space-y-3">
        {projects.map((project) => {
          const cfg = STATUS_CONFIG[project.status] || STATUS_CONFIG.pending
          const StatusIcon = cfg.icon

          return (
            <div
              key={project.id}
              onClick={() => navigate(`/projects/${project.id}`)}
              className="glass-card p-5 flex items-center gap-4 cursor-pointer
                         hover:border-accent/30 hover:bg-hover/50 transition-all duration-200 group"
            >
              {/* Icon */}
              <div className="w-11 h-11 rounded-xl bg-accent/10 flex items-center justify-center shrink-0">
                <FileVideo size={20} className="text-accent-light" />
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <h3 className="font-semibold text-ink-primary truncate">
                    {project.name || project.original_filename}
                  </h3>
                  <span className={cfg.badge}>
                    <StatusIcon size={12} className={project.status === 'processing' ? 'animate-spin' : ''} />
                    {cfg.label}
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-ink-muted">
                  <span>{formatDate(project.created_at)}</span>
                  {project.file_size > 0 && (
                    <>
                      <span>•</span>
                      <span>{formatSize(project.file_size)}</span>
                    </>
                  )}
                  {project.clips?.length > 0 && (
                    <>
                      <span>•</span>
                      <span>{project.clips.length} clip{project.clips.length !== 1 ? 's' : ''}</span>
                    </>
                  )}
                </div>
                {/* Prompt preview */}
                <p className="text-xs text-ink-secondary mt-1.5 truncate max-w-md">
                  {project.prompt}
                </p>
              </div>

              {/* Progress bar for processing */}
              {project.status === 'processing' && (
                <div className="w-24 shrink-0">
                  <div className="flex justify-between text-[10px] text-ink-muted mb-1">
                    <span>{project.processing_stage?.replace('_', ' ') || 'starting'}</span>
                    <span>{project.progress}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-surface rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-accent rounded-full transition-all duration-500"
                      style={{ width: `${project.progress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={(e) => handleDelete(e, project.id)}
                  className="p-2 rounded-lg hover:bg-danger/15 text-ink-muted hover:text-danger transition-colors"
                  title="Delete project"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
