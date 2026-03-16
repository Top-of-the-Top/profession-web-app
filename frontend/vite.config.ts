import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@app": path.resolve(__dirname, "src/app"),
			"@assets": path.resolve(__dirname, "./src/assets"),
			"@entities": path.resolve(__dirname, "./src/entities"),
			"@pages": path.resolve(__dirname, "./src/pages"),
			"@shared": path.resolve(__dirname, "src/shared"),
			"@widgets": path.resolve(__dirname, "./src/widgets"),
    },
  },
	server: {
		allowedHosts: ['professionkid.ru', 'www.professionkid.ru'],
		host: '0.0.0.0',
		port: 3000,
		watch: {
			usePolling: true,
		},
		hmr: {
			clientPort: 3000,
		},
	},
	
});