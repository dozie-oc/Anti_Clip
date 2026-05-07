import { useState, useEffect } from 'react'
import { Settings, Key, Cpu, HardDrive, Info, ExternalLink, CheckCircle } from 'lucide-react'
import { checkHealth } from '@/services/api'
import toast from 'react-hot-toast'

export default function SettingsPage() {
  const [health, setHealth] = useState(null)

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch(() => toast.error('Could not connect to backend'))
  }, [])

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold gradient-text">Settings</h1>
        <p className="text-ink-secondary mt-1">
          System configuration and status
        </p>
      </div>

      {/* System status */}
      <div className="glass-card p-6 space-y-4">
        <h2 className="section-title flex items-center gap-2">
          <HardDrive size={18} className="text-accent-light" />
          System Status
        </h2>

        {health ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-surface rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
                <span className="text-sm font-semibold text-ink-primary">Backend</span>
              </div>
              <p className="text-xs text-ink-secondary">Connected and running</p>
            </div>

            <div className="p-4 bg-surface rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-1">
                <Cpu size={14} className="text-accent-light" />
                <span className="text-sm font-semibold text-ink-primary">Whisper Model</span>
              </div>
              <p className="text-xs text-ink-secondary capitalize">{health.whisper_model}</p>
            </div>

            <div className="p-4 bg-surface rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-1">
                <Key size={14} className={health.llm_configured ? 'text-success' : 'text-warning'} />
                <span className="text-sm font-semibold text-ink-primary">LLM Provider</span>
              </div>
              <p className="text-xs text-ink-secondary">
                {health.llm_configured ? (
                  <span className="flex items-center gap-1 text-success">
                    <CheckCircle size={12} /> OpenAI ({health.llm_model}) connected
                  </span>
                ) : (
                  <span className="text-warning">
                    Fallback mode — set OPENAI_API_KEY for AI scoring
                  </span>
                )}
              </p>
            </div>

            <div className="p-4 bg-surface rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-1">
                <Info size={14} className="text-info" />
                <span className="text-sm font-semibold text-ink-primary">FFmpeg</span>
              </div>
              <p className="text-xs text-ink-secondary">Required for video processing</p>
            </div>
          </div>
        ) : (
          <div className="p-8 text-center">
            <div className="w-3 h-3 rounded-full bg-danger mx-auto mb-2" />
            <p className="text-sm text-danger">Cannot connect to backend</p>
            <p className="text-xs text-ink-muted mt-1">
              Make sure the server is running on port 8000
            </p>
          </div>
        )}
      </div>

      {/* Configuration guide */}
      <div className="glass-card p-6 space-y-4">
        <h2 className="section-title flex items-center gap-2">
          <Settings size={18} className="text-accent-light" />
          Configuration
        </h2>

        <div className="space-y-3">
          <div className="p-4 bg-surface rounded-lg border border-border">
            <h3 className="text-sm font-semibold text-ink-primary mb-2">
              OpenAI API Key
            </h3>
            <p className="text-xs text-ink-secondary mb-3">
              Add your OpenAI API key to enable intelligent clip scoring. Without it, the system
              uses heuristic-based scoring as a fallback.
            </p>
            <div className="bg-base rounded-lg p-3 border border-border">
              <code className="text-xs text-accent-light font-mono">
                # backend/.env<br />
                OPENAI_API_KEY=sk-your-key-here<br />
                LLM_MODEL_NAME=gpt-4o
              </code>
            </div>
          </div>

          <div className="p-4 bg-surface rounded-lg border border-border">
            <h3 className="text-sm font-semibold text-ink-primary mb-2">
              Whisper Model
            </h3>
            <p className="text-xs text-ink-secondary mb-2">
              Choose a Whisper model size. Larger models are more accurate but slower.
            </p>
            <div className="flex gap-2 flex-wrap">
              {['tiny', 'base', 'small', 'medium', 'large'].map((m) => (
                <span
                  key={m}
                  className={`
                    px-3 py-1.5 rounded-lg text-xs font-medium border
                    ${health?.whisper_model === m
                      ? 'bg-accent/15 text-accent-light border-accent/30'
                      : 'bg-surface text-ink-muted border-border'
                    }
                  `}
                >
                  {m}
                </span>
              ))}
            </div>
          </div>

          <div className="p-4 bg-surface rounded-lg border border-border">
            <h3 className="text-sm font-semibold text-ink-primary mb-2">
              Prerequisites
            </h3>
            <ul className="space-y-2 text-xs text-ink-secondary">
              <li className="flex items-start gap-2">
                <span className="text-accent-light mt-0.5">•</span>
                <span><strong>FFmpeg</strong> — must be installed and in your system PATH</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-accent-light mt-0.5">•</span>
                <span><strong>Python 3.11+</strong> — required for the backend</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-accent-light mt-0.5">•</span>
                <span><strong>Node.js 18+</strong> — required for the frontend</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-accent-light mt-0.5">•</span>
                <span><strong>CUDA (optional)</strong> — GPU acceleration for Whisper</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* About */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-accent flex items-center justify-center shadow-glow-sm">
            <span className="text-white font-bold text-lg">A</span>
          </div>
          <div>
            <h3 className="font-semibold text-ink-primary">AntiClip v1.0.0</h3>
            <p className="text-xs text-ink-secondary">
              Local-first AI video clipping platform
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
