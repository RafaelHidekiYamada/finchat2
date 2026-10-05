/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#17201d',
        cream: '#f5f3ed',
        pine: '#164f3f',
        mint: '#d8eadf',
        coral: '#dd694c',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
        display: ['Manrope', 'Inter', 'ui-sans-serif'],
      },
      boxShadow: { card: '0 18px 50px -30px rgba(23,32,29,.35)' },
    },
  },
  plugins: [],
}
