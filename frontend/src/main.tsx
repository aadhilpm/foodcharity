import React from 'react'
import ReactDOM from 'react-dom/client'
import { FrappeProvider } from 'frappe-react-sdk'
import App from './App'
import './index.css'

// Get the site URL - in production, this will be the same origin
const getSiteUrl = () => {
  // For development, you can set this to your Frappe site URL
  return window.location.origin
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <FrappeProvider
      url={getSiteUrl()}
      enableSocket={false}
    >
      <App />
    </FrappeProvider>
  </React.StrictMode>
)
