import { NavLink, useLocation } from 'react-router-dom'
import {
  Upload, FolderOpen, ListVideo, Settings, Scissors, Zap
} from 'lucide-react'

const NAV = [
  { to: '/upload',   icon: Upload,     label: 'Upload Video' },
  { to: '/projects', icon: FolderOpen, label: 'Projects'     },
  { to: '/queue',    icon: ListVideo,  label: 'Queue'        },
  { to: '/settings', icon: Settings,   label: 'Settings'     },
]

export default function Sidebar() {
  const { pathname } = useLocation()

  return (
    <aside className="flex flex-col w-56 min-h-screen bg-surface border-r border-border shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-border">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-accent shadow-glow-sm">
          <Scissors size={15} className="text-white" />
        </div>
        <span className="font-bold text-lg tracking-tight gradient-text">AntiClip</span>
      </div>

      {/* Nav links */}
      <nav className="flex flex-col gap-1 p-3 flex-1">
        {NAV.map(({ to, icon: Icon, label }) => {
          const active = pathname.startsWith(to)
          return (
            <NavLink
              key={to}
              to={to}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150
                ${active
                  ? 'bg-accent/15 text-accent-light border border-accent/20'
                  : 'text-ink-secondary hover:text-ink-primary hover:bg-hover'
                }`}
            >
              <Icon size={17} className={active ? 'text-accent-light' : ''} />
              {label}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer badge */}
      <div className="px-4 py-4 border-t border-border">
        <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-accent/10 border border-accent/20">
          <Zap size={14} className="text-accent-light shrink-0" />
          <div>
            <p className="text-xs font-semibold text-accent-light">AI Ready</p>
            <p className="text-[10px] text-ink-muted leading-tight">Connect your AI model</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
