/**
 * Global Zustand store — upload state + staged files.
 */
import { create } from 'zustand'

export const useAppStore = create((set, get) => ({
  // ── Staged uploads (files selected but not yet in a project) ─────────────
  stagedFiles: [],       // File objects from the file picker
  uploadedMeta: [],      // Response from POST /upload (file_id, original_name, size…)
  uploadProgress: 0,
  isUploading: false,
  uploadError: null,

  setStagedFiles: (files) => set({ stagedFiles: files }),
  addStagedFiles: (files) =>
    set((s) => ({ stagedFiles: [...s.stagedFiles, ...files] })),
  removeStagedFile: (name) =>
    set((s) => ({
      stagedFiles: s.stagedFiles.filter((f) => f.name !== name),
      uploadedMeta: s.uploadedMeta.filter((m) => m.original_name !== name),
    })),
  clearStaged: () =>
    set({ stagedFiles: [], uploadedMeta: [], uploadProgress: 0, uploadError: null }),

  setUploadProgress: (pct) => set({ uploadProgress: pct }),
  setIsUploading: (v)      => set({ isUploading: v }),
  setUploadError: (e)      => set({ uploadError: e }),
  setUploadedMeta: (meta)  => set({ uploadedMeta: meta }),

  // ── Projects list cache ──────────────────────────────────────────────────
  projects: [],
  projectsLoading: false,
  setProjects: (p)         => set({ projects: p }),
  setProjectsLoading: (v)  => set({ projectsLoading: v }),
  updateProject: (updated) =>
    set((s) => ({
      projects: s.projects.map((p) => (p.id === updated.id ? updated : p)),
    })),
  removeProject: (id) =>
    set((s) => ({ projects: s.projects.filter((p) => p.id !== id) })),

  // ── Active page / sidebar ────────────────────────────────────────────────
  activePage: 'upload',
  setActivePage: (page) => set({ activePage: page }),
}))
