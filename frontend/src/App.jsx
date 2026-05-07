import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import UploadPage        from '@/pages/UploadPage'
import ProjectsPage      from '@/pages/ProjectsPage'
import ProjectDetailPage from '@/pages/ProjectDetailPage'
import QueuePage         from '@/pages/QueuePage'
import SettingsPage      from '@/pages/SettingsPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/"                   element={<Navigate to="/upload" replace />} />
        <Route path="/upload"             element={<UploadPage />} />
        <Route path="/projects"           element={<ProjectsPage />} />
        <Route path="/projects/:id"       element={<ProjectDetailPage />} />
        <Route path="/queue"              element={<QueuePage />} />
        <Route path="/settings"           element={<SettingsPage />} />
      </Routes>
    </Layout>
  )
}
