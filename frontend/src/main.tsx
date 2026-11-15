import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/public-sans/wght.css'
import '@fontsource/dm-mono/latin-400.css'
import '@fontsource/dm-mono/latin-500.css'
import { ApplicationBoundary, ApplicationError, ApplicationLoading } from './components/ApplicationError'
import { startApplication } from './startApplication'
import './styles.css'

const root = document.getElementById('root')
if (!root) throw new Error('The application root is missing.')

const applicationRoot = createRoot(root)
applicationRoot.render(<ApplicationLoading />)

void startApplication(
  () => import('./App'),
  ({ App }) => applicationRoot.render(<StrictMode><ApplicationBoundary><App /></ApplicationBoundary></StrictMode>),
  () => {
    console.error('Flight Log startup failed; check application loading and connection configuration.')
    applicationRoot.render(<ApplicationError startup />)
  },
)
