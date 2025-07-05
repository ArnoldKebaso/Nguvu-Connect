/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.{html,js}',
    './templates/pages/**/*.{html,js}',
    './templates/components/**/*.{html,js}'
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#1E40AF',
          light: '#3B82F6'
        },
        success: '#10B981',
        warning: '#FBBF24'
      }
    }
  },
  plugins: [],
}