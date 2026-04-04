/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Paleta NemoOC — replica colores del desktop
        nemo: {
          bg:      '#1a1a2e',
          sidebar: '#16213e',
          panel:   '#0f3460',
          accent:  '#3b82f6',
          hover:   '#2563eb',
        },
        // Estados OC
        estado: {
          nueva:     '#1e40af',
          ingresada: '#065f46',
          proceso:   '#92400e',
        },
        // Homologación
        homo: {
          ok:       '#166534',
          pending:  '#92400e',
          manual:   '#1e40af',
          missing:  '#7f1d1d',
        },
      },
    },
  },
  plugins: [],
}
