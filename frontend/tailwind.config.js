/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Background layers
        base:    '#07070f',
        surface: '#0e0e1a',
        card:    '#141426',
        hover:   '#1c1c30',
        // Border
        border:  '#272740',
        // Accent — vivid violet
        accent: {
          DEFAULT: '#7c3aed',
          light:   '#a78bfa',
          dark:    '#5b21b6',
          glow:    'rgba(124,58,237,0.35)',
        },
        // Text
        ink: {
          primary:   '#eeeeff',
          secondary: '#8888aa',
          muted:     '#55556a',
        },
        // Status
        success: '#10d48e',
        warning: '#f5a623',
        danger:  '#ff4d6d',
        info:    '#38bdf8',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glow:  '0 0 24px rgba(124,58,237,0.4)',
        'glow-sm': '0 0 12px rgba(124,58,237,0.25)',
        card:  '0 4px 24px rgba(0,0,0,0.4)',
      },
      backgroundImage: {
        'gradient-accent': 'linear-gradient(135deg, #7c3aed 0%, #a855f7 100%)',
        'gradient-surface': 'linear-gradient(180deg, #141426 0%, #0e0e1a 100%)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        'slide-up':   'slideUp 0.3s ease-out',
        'fade-in':    'fadeIn 0.25s ease-out',
      },
      keyframes: {
        slideUp: {
          '0%':   { transform: 'translateY(12px)', opacity: '0' },
          '100%': { transform: 'translateY(0)',    opacity: '1' },
        },
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
