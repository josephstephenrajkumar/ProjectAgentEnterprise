/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0B0F19',
        surface: '#1A2332',
        primary: '#3B82F6',
        secondary: '#10B981',
        accent: '#8B5CF6',
        textPrimary: '#F3F4F6',
        textSecondary: '#9CA3AF',
        border: '#2A3441'
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
