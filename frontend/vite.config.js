import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  return {
    cacheDir: env.VITE_CACHE_DIR || "node_modules/.vite",
    plugins: [vue()],
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: env.VITE_DJANGO_API_URL || "http://127.0.0.1:8000",
          changeOrigin: true
        },
        "/matching-api": {
          target: "http://127.0.0.1:8001",
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/matching-api/, "")
        }
      }
    }
  };
});
