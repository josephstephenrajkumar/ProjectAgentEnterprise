/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0d1017',
        surface: '#161923',
        primary: '#6366f1',
        secondary: '#10B981',
        accent: '#8B5CF6',
        textPrimary: '#f8fafc',
        textSecondary: '#94a3b8',
        border: '#2a2f3d'
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
