import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#141426',
            color: '#eeeeff',
            border: '1px solid #272740',
            borderRadius: '10px',
            fontSize: '14px',
          },
          success: { iconTheme: { primary: '#10d48e', secondary: '#141426' } },
          error:   { iconTheme: { primary: '#ff4d6d', secondary: '#141426' } },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>
)
