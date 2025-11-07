import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { UploadValidatePage } from './pages/UploadValidate/UploadValidatePage'
import { ZoningWorkspacePage } from './pages/ZoningWorkspace/ZoningWorkspacePage'
import { RoutingWorkspacePage } from './pages/RoutingWorkspace/RoutingWorkspacePage'
import { ReportsPage } from './pages/Reports/ReportsPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<Navigate to="/upload" replace />} />
        <Route path="upload" element={<UploadValidatePage />} />
        <Route path="zoning" element={<ZoningWorkspacePage />} />
        <Route path="routing" element={<RoutingWorkspacePage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="*" element={<Navigate to="/upload" replace />} />
      </Route>
    </Routes>
  )
}
