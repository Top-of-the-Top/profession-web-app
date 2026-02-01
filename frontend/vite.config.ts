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
    host: '127.0.0.1',
    port: 3000,
  },
});