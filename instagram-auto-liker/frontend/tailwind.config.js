/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ig: {
          pink: '#E1306C',
          purple: '#833AB4',
          orange: '#F77737',
        },
      },
    },
  },
  plugins: [],
};
