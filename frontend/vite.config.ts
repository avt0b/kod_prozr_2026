import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    watch: { ignored: ['**/e2e/**', '**/test-results/**'] },
    proxy: { '/api': 'http://127.0.0.1:8000' },
    port: 5173,
    host: true,
  },
  preview: {
    port: 4173,
  },
  build: {
    chunkSizeWarningLimit: 1500,
  },
});
