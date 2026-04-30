/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    // Templates
    '../../templates/**/*.html',
    '../../**/templates/**/*.html',
    // Theme
    './src/**/*.css',
  ],
  theme: {
    extend: {
      colors: {
        // White-label overridable via CSS custom properties (1Claw skin)
        brand: {
          primary: 'var(--primary, #990029)',
          'primary-hover': 'var(--primary-hover, #7A0021)',
          secondary: 'var(--brand-600, #B80030)',
        },
      },
      fontFamily: {
        wordmark: ['var(--brand-font-wordmark)', 'sans-serif'],
        display: ['var(--brand-font-display)', 'sans-serif'],
        sans: ['var(--brand-font-body)', 'sans-serif'],
        mono: ['var(--brand-font-mono)', 'monospace'],
      },
    },
  },
  plugins: [],
}
