import { Navigate, RouterProvider, createHashRouter } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { AlertsPage } from './pages/AlertsPage'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { DashboardPage } from './pages/DashboardPage'
import { JournalPage } from './pages/JournalPage'
import { NotFoundPage } from './pages/NotFoundPage'

/**
 * Hash routing keeps reload and Back/Forward working on any static host. A data router is
 * used so the Journal can ask before a navigation discards unsaved changes.
 */
const router = createHashRouter([
  {
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'analytics', element: <AnalyticsPage /> },
      { path: 'alerts', element: <AlertsPage /> },
      { path: 'alerts/:alertId', element: <AlertsPage /> },
      { path: 'journal', element: <JournalPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

export function App() {
  return <RouterProvider router={router} />
}
