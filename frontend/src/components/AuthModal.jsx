import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import './AuthModal.css'

export default function AuthModal({ onClose }) {
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { googleLogin } = useAuth()
  const googleButtonRef = useRef(null)

  // Handle Google Sign-In
  useEffect(() => {
    // Load Google Identity Services script
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true
    document.body.appendChild(script)

    script.onload = () => {
      if (window.google && googleButtonRef.current) {
        window.google.accounts.id.initialize({
          client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID || '',
          callback: handleGoogleCallback,
        })
        
        window.google.accounts.id.renderButton(googleButtonRef.current, {
          theme: 'filled_black',
          size: 'large',
          width: '100%',
          text: 'signin_with',
        })
      }
    }

    return () => {
      if (document.body.contains(script)) {
        document.body.removeChild(script)
      }
    }
  }, [])

  const handleGoogleCallback = async (response) => {
    setError('')
    setLoading(true)
    
    try {
      await googleLogin(response.credential)
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-modal-overlay" onClick={onClose}>
      <div className="auth-modal" onClick={e => e.stopPropagation()}>
        <button className="auth-modal-close" onClick={onClose}>✕</button>
        
        <h2>Sign In</h2>
        
        <p className="auth-subtitle">Sign in with Google to continue</p>
        
        {error && <div className="auth-error">{error}</div>}
        
        {/* Google Sign-In Button */}
        <div ref={googleButtonRef} className="google-btn-container"></div>
        
        {loading && <p className="auth-loading">Signing in...</p>}
      </div>
    </div>
  )
}
