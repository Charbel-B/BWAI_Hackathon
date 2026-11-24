import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './app/app'
import './index.css'

const root = document.getElementById('root')
if (root === null) throw new Error('élément #root absent de index.html')

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
