/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#0F172A', // Slate 900
          dark: '#020617',
        },
        secondary: {
          DEFAULT: '#1E293B', // Slate 800
          light: '#334155',
        },
        accent: {
          DEFAULT: '#2563EB', // Blue 600
          light: '#3B82F6',
          dark: '#1D4ED8',
        },
        success: '#22C55E', // Green 500
        warning: '#F59E0B', // Amber 500
        danger: '#DC2626',  // Red 600
        background: '#F8FAFC', // Slate 50
        card: '#FFFFFF',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
        display: ['IBM Plex Sans', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
