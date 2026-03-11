/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        ink:     '#0A0A0F',
        surface: '#111118',
        panel:   '#16161F',
        border:  '#2A2A38',
        muted:   '#3A3A4A',
        subtle:  '#6B6B80',
        body:    '#A8A8B8',
        heading: '#E8E8F0',
        gold:    '#C9A84C',
        'gold-dim': '#8A6E32',
        red:     '#E05252',
        amber:   '#D4882A',
        green:   '#4CAF7C',
      },
      fontFamily: {
        display: ['var(--font-display)'],
        body:    ['var(--font-body)'],
        mono:    ['var(--font-mono)'],
      },
    },
  },
  plugins: [],
}