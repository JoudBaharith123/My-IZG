/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#3713ec',
        'background-light': '#f6f6f8',
        'background-dark': '#131022',
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '0.5rem',
        lg: '1rem',
        xl: '1.5rem',
      },
    },
  },
  plugins: [require('@tailwindcss/forms')],
}
