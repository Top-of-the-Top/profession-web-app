import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    dedupe: ['react', 'react-dom'],
    alias: {
      "@app": path.resolve(__dirname, "src/app"),
      "@assets": path.resolve(__dirname, "./src/assets"),
      "@entities": path.resolve(__dirname, "./src/entities"),
      "@pages": path.resolve(__dirname, "./src/pages"),
      "@router": path.resolve(__dirname, "./src/router"),
      "@schemas": path.resolve(__dirname, "./src/schemas"),
      "@shared": path.resolve(__dirname, "src/shared"),
      "@widgets": path.resolve(__dirname, "./src/widgets"),
      "@components": path.resolve(__dirname, "./src/components"),
      react: path.resolve(__dirname, './node_modules/react'),
      'react-dom': path.resolve(__dirname, './node_modules/react-dom'),
      'react/jsx-runtime': path.resolve(__dirname, './node_modules/react/jsx-runtime.js'),
      'react/jsx-dev-runtime': path.resolve(__dirname, './node_modules/react/jsx-dev-runtime.js'),
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
      },
    },
  },
});