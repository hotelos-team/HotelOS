import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const target = env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';
  return {
    server: {
      proxy: {
        '/backend': {
          target,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/backend/, ''),
        },
      },
    },
  };
});
