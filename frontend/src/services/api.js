/**
 * API service — all calls to the FastAPI backend.
 * The Vite dev proxy forwards /api/* → http://localhost:8000
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120_000, // 2 min for large uploads
})

// ── Interceptors ────────────────────────────────────────────────────────────
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail || err.message || 'Unknown error'
    return Promise.reject(new Error(message))
  }
)

// ── Upload ──────────────────────────────────────────────────────────────────
/**
 * Upload a video file with optional settings.
 */
export async function uploadVideo(file, config = {}, onProgress) {
  const form = new FormData()
  form.append('file', file)
  form.append('prompt', config.prompt || '')
  form.append('clip_mode', config.clip_mode || 'short')
  form.append('processing_mode', config.processing_mode || 'clips')

  const { data } = await api.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300_000, // 5 min for large files
    onUploadProgress(e) {
      if (e.total) onProgress?.(Math.round((e.loaded / e.total) * 100))
    },
  })
  return data
}

// ── Projects ────────────────────────────────────────────────────────────────
export async function fetchProjects() {
  const { data } = await api.get('/projects')
  return data
}

export async function fetchProject(id) {
  const { data } = await api.get(`/projects/${id}`)
  return data
}

export async function deleteProject(id) {
  await api.delete(`/projects/${id}`)
}

export async function updateProject(id, updates) {
  const { data } = await api.patch(`/projects/${id}`, null, { params: updates })
  return data
}

export async function resetProject(id) {
  const { data } = await api.post(`/projects/${id}/reset`)
  return data
}

// ── Processing ──────────────────────────────────────────────────────────────
/**
 * Start processing with full mode configuration.
 */
export async function startProcessing(projectId, config = {}) {
  // Use the new ProcessRequest schema (sent as JSON body)
  const { data } = await api.post(`/projects/${projectId}/process`, config)
  return data
}

// ── Job status ──────────────────────────────────────────────────────────────
export async function fetchJobStatus(projectId) {
  const { data } = await api.get(`/projects/${projectId}/job`)
  return data
}

// ── Health ──────────────────────────────────────────────────────────────────
export async function checkHealth() {
  const { data } = await axios.get('/health', { timeout: 5000 })
  return data
}

// ── Clip URL helper ─────────────────────────────────────────────────────────
export function getClipUrl(projectId, filename) {
  return `/clips/${projectId}/${filename}`
}

export default api
