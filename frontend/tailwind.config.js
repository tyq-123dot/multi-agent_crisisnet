/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'fire': {
          100: '#fff7ed',
          200: '#ffedd5',
          300: '#fed7aa',
          400: '#fdba74',
          500: '#fb923c',
          600: '#ea580c',
          700: '#c2410c',
          800: '#9a3412',
          900: '#7c2d12',
        },
        'flood': {
          100: '#eff6ff',
          200: '#dbeafe',
          300: '#bfdbfe',
          400: '#93c5fd',
          500: '#60a5fa',
          600: '#3b82f6',
          700: '#2563eb',
        }
      },
      animation: {
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 2s infinite',
      }
    },
  },
  plugins: [],
}