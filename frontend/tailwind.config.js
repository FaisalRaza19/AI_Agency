/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        google: {
          blue: '#1a73e8',
          blueHover: '#1557b0',
          darkBg: '#121212',
          cardDark: '#1e1e1e',
          sidebarDark: '#202124',
          borderDark: '#2d2d2d',
          textMuted: '#9aa0a6',
        }
      }
    },
  },
  plugins: [],
}
