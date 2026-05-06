/**
 * useUpload — handles file selection → upload → project creation flow.
 */
import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { uploadFiles, createProject } from '@/services/api'
import { useAppStore } from '@/store/appStore'

export function useUpload() {
  const navigate = useNavigate()
  const {
    stagedFiles, addStagedFiles, removeStagedFile, clearStaged,
    uploadedMeta, setUploadedMeta,
    setUploadProgress, setIsUploading, setUploadError,
    isUploading, uploadProgress, uploadError,
    setProjects, projects,
  } = useAppStore()

  /** Add files from the dropzone to the staged list */
  const stageFiles = useCallback((newFiles) => {
    const allowed = ['.mp4', '.mkv', '.mov', '.avi', '.webm']
    const valid = newFiles.filter((f) => {
      const ext = '.' + f.name.split('.').pop().toLowerCase()
      if (!allowed.includes(ext)) {
        toast.error(`"${f.name}" is not a supported video format.`)
        return false
      }
      return true
    })
    addStagedFiles(valid)
  }, [addStagedFiles])

  /** Upload all staged files to the backend */
  const uploadStaged = useCallback(async () => {
    if (!stagedFiles.length) return

    setIsUploading(true)
    setUploadError(null)
    setUploadProgress(0)

    try {
      const results = await uploadFiles(stagedFiles, setUploadProgress)
      setUploadedMeta(results)
      toast.success(`${results.length} file(s) uploaded successfully.`)
      return results
    } catch (err) {
      setUploadError(err.message)
      toast.error(`Upload failed: ${err.message}`)
      return null
    } finally {
      setIsUploading(false)
    }
  }, [stagedFiles, setIsUploading, setUploadError, setUploadProgress, setUploadedMeta])

  /** Create a project from uploaded files + prompt/settings */
  const submitProject = useCallback(async ({ prompt, settings }) => {
    if (!uploadedMeta.length) {
      toast.error('Please upload files first.')
      return
    }
    try {
      const project = await createProject({
        prompt,
        settings,
        file_ids: uploadedMeta.map((m) => m.file_id),
      })
      setProjects([project, ...projects])
      clearStaged()
      toast.success('Project created! Ready to generate clips.')
      navigate('/projects')
    } catch (err) {
      toast.error(`Failed to create project: ${err.message}`)
    }
  }, [uploadedMeta, projects, setProjects, clearStaged, navigate])

  return {
    stagedFiles,
    uploadedMeta,
    uploadProgress,
    isUploading,
    uploadError,
    stageFiles,
    removeStagedFile,
    clearStaged,
    uploadStaged,
    submitProject,
  }
}
