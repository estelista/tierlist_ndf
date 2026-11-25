import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import '@fontsource/titan-one/latin.css'
import '@fontsource/bowlby-one/latin.css'
import '@fontsource/shrikhand/latin.css'
import '@fontsource-variable/familjen-grotesk/wght.css'
import './index.css'
import './App.css'
import App from './App.jsx'
import { conferirLogin } from './api.js'

conferirLogin()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
