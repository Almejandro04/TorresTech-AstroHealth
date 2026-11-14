import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { AlertsPage } from './pages/AlertsPage'
import { JournalPage } from './pages/JournalPage'
import { NotFoundPage } from './pages/NotFoundPage'

export function App() {
  return <HashRouter><Routes><Route element={<AppShell />}>
    <Route index element={<Navigate to="/dashboard" replace />} />
    <Route path="dashboard" element={<DashboardPage />} />
    <Route path="analytics" element={<AnalyticsPage />} />
    <Route path="alerts" element={<AlertsPage />} />
    <Route path="journal" element={<JournalPage />} />
    <Route path="*" element={<NotFoundPage />} />
  </Route></Routes></HashRouter>
}
