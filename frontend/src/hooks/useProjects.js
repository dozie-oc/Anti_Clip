/**
 * useProjects — fetches projects and polls processing ones for updates.
 */
import { useCallback, useEffect, useRef } from 'react'
import { fetchProjects, fetchProject, deleteProject, startProcessing } from '@/services/api'
import { useAppStore } from '@/store/appStore'
import toast from 'react-hot-toast'

const POLL_INTERVAL = 2500 // ms

export function useProjects() {
  const { projects, setProjects, setProjectsLoading, updateProject, removeProject, projectsLoading } = useAppStore()
  const pollRef = useRef(null)

  const load = useCallback(async () => {
    setProjectsLoading(true)
    try {
      const data = await fetchProjects()
      setProjects(data)
    } catch (err) {
      toast.error(`Could not load projects: ${err.message}`)
    } finally {
      setProjectsLoading(false)
    }
  }, [setProjects, setProjectsLoading])

  /** Poll any project that is currently processing */
  const pollProcessing = useCallback(async () => {
    const processing = projects.filter((p) => p.status === 'processing')
    if (!processing.length) return
    await Promise.all(
      processing.map(async (p) => {
        try {
          const updated = await fetchProject(p.id)
          updateProject(updated)
        } catch { /* ignore */ }
      })
    )
  }, [projects, updateProject])

  // Initial load
  useEffect(() => { load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Set up polling
  useEffect(() => {
    pollRef.current = setInterval(pollProcessing, POLL_INTERVAL)
    return () => clearInterval(pollRef.current)
  }, [pollProcessing])

  const handleDelete = useCallback(async (id) => {
    try {
      await deleteProject(id)
      removeProject(id)
      toast.success('Project deleted.')
    } catch (err) {
      toast.error(`Delete failed: ${err.message}`)
    }
  }, [removeProject])

  const handleProcess = useCallback(async (id) => {
    try {
      await startProcessing(id)
      // Optimistically update status
      updateProject({ ...projects.find((p) => p.id === id), status: 'processing', progress: 0 })
      toast.success('Processing started!')
    } catch (err) {
      toast.error(err.message)
    }
  }, [projects, updateProject])

  return { projects, projectsLoading, reload: load, handleDelete, handleProcess }
}
