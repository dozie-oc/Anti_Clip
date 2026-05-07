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
 * Upload a video file with optional prompt.
 * @param {File} file
 * @param {string} prompt
 * @param {(pct: number) => void} onProgress
 */
export async function uploadVideo(file, prompt, onProgress) {
  const form = new FormData()
  form.append('file', file)
  form.append('prompt', prompt || '')

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
export async function startProcessing(projectId, prompt) {
  const params = prompt ? { prompt } : {}
  const { data } = await api.post(`/projects/${projectId}/process`, null, { params })
  return data
}

// ── Job status ──────────────────────────────────────────────────────────────
export async function fetchJobStatus(projectId) {
  const { data } = await api.get(`/projects/${projectId}/job`)
  return data
}

// ── Health ──────────────────────────────────────────────────────────────────
export async function checkHealth() {
  const { data } = await api.get('/health')
  return data
}

// ── Clip URL helper ─────────────────────────────────────────────────────────
export function getClipUrl(projectId, filename) {
  return `/clips/${projectId}/${filename}`
}

export default api
