/**
 * API service layer — all calls to the FastAPI backend go through here.
 * The Vite dev proxy forwards /api/* → http://localhost:8000
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
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
 * Upload one or more video files.
 * @param {File[]} files
 * @param {(pct: number) => void} onProgress
 * @returns {Promise<Array>}
 */
export async function uploadFiles(files, onProgress) {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))

  const { data } = await api.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress(e) {
      if (e.total) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
  return data
}

// ── Projects ────────────────────────────────────────────────────────────────
export async function createProject(payload) {
  const { data } = await api.post('/projects/create', payload)
  return data
}

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

// ── Processing ──────────────────────────────────────────────────────────────
export async function startProcessing(projectId) {
  const { data } = await api.post(`/projects/${projectId}/process`)
  return data
}

// ── Health ──────────────────────────────────────────────────────────────────
export async function checkHealth() {
  const { data } = await api.get('/health')
  return data
}

export default api
