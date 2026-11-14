import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  define: {
    'import.meta.env.VITE_API_KEY': JSON.stringify(
      process.env.VITE_API_KEY || process.env.AIIOT_API_KEY || ''
    ),
  },
  server: {
    host: '0.0.0.0',
  },
});
