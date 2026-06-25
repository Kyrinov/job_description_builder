import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './app.jsx'   // lowercase — matches new file (Plan 03)
import './styles.css'          // replaces index.css

const root = createRoot(document.getElementById('root'))
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
