import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/public-sans/wght.css'
import '@fontsource/dm-mono/latin-400.css'
import '@fontsource/dm-mono/latin-500.css'
import { App } from './App'
import './styles.css'

const root = document.getElementById('root')
if (!root) throw new Error('The application root is missing.')

createRoot(root).render(<StrictMode><App /></StrictMode>)
