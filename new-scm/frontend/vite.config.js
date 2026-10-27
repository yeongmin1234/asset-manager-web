import { defineConfig } from "vite";

export default defineConfig({
  server: {
    proxy: {
      "/api/v1": {
        target: "http://127.0.0.1:8012",
        changeOrigin: false,
      },
    },
  },
});
