/**
 * Global Zustand store — manages upload state, projects, and active views.
 */
import { create } from 'zustand'

export const useAppStore = create((set, get) => ({
  // ── Upload state ────────────────────────────────────────────────────────
  uploadProgress: 0,
  isUploading: false,
  uploadError: null,

  setUploadProgress: (pct) => set({ uploadProgress: pct }),
  setIsUploading: (v) => set({ isUploading: v }),
  setUploadError: (e) => set({ uploadError: e }),
  resetUpload: () =>
    set({ uploadProgress: 0, isUploading: false, uploadError: null }),

  // ── Projects list cache ─────────────────────────────────────────────────
  projects: [],
  projectsLoading: false,
  setProjects: (p) => set({ projects: p }),
  setProjectsLoading: (v) => set({ projectsLoading: v }),
  updateProject: (updated) =>
    set((s) => ({
      projects: s.projects.map((p) => (p.id === updated.id ? updated : p)),
    })),
  addProject: (project) =>
    set((s) => ({ projects: [project, ...s.projects] })),
  removeProject: (id) =>
    set((s) => ({ projects: s.projects.filter((p) => p.id !== id) })),

  // ── Active project detail ───────────────────────────────────────────────
  activeProject: null,
  setActiveProject: (p) => set({ activeProject: p }),

  // ── Sidebar page ───────────────────────────────────────────────────────
  activePage: 'upload',
  setActivePage: (page) => set({ activePage: page }),
}))
