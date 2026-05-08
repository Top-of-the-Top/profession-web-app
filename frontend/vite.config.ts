import path from 'path';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  build: {
    sourcemap: false,
    rollupOptions: {
      onwarn(warning, warn) {
        const isMathJsPureAnnotationWarning =
          warning.code === 'SOURCEMAP_ERROR' &&
          typeof warning.message === 'string' &&
          warning.message.includes(
            'contains an annotation that Rollup cannot interpret due to the position of the comment',
          ) &&
          warning.message.includes('node_modules/mathjs/');

        if (isMathJsPureAnnotationWarning) {
          return;
        }

        warn(warning);
      },
    },
  },
  resolve: {
    alias: {
      '@app': path.resolve(__dirname, 'src/app'),
      '@assets': path.resolve(__dirname, './src/assets'),
      '@entities': path.resolve(__dirname, './src/entities'),
      '@pages': path.resolve(__dirname, './src/pages'),
      '@router': path.resolve(__dirname, './src/router'),
      '@schemas': path.resolve(__dirname, './src/schemas'),
      '@shared': path.resolve(__dirname, 'src/shared'),
      '@widgets': path.resolve(__dirname, './src/widgets'),
      '@components': path.resolve(__dirname, './src/components'),
    },
  },
  server: {
    allowedHosts: [
      'professionkid.ru',
      'www.professionkid.ru',
      'unequal-wildfowl-dreamy.ngrok-free.dev',
      'professionkid-testing.ru',
      'www.professionkid-testing.ru',
    ],
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://backend:9000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
