import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath } from 'node:url';
export default defineConfig({ envDir: fileURLToPath(new URL('./config', import.meta.url)), plugins: [vue()], resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } }, server: { host: '127.0.0.1', port: 3000, strictPort: true }, preview: { host: '127.0.0.1', port: 3000, strictPort: true } });
