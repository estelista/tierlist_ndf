import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Em desenvolvimento o Vite repassa a API e as fotos para o Django. Assim o site também
// abre no celular (npm run celular), sem mexer no CORS nem no ALLOWED_HOSTS.
// Para usar outro backend, defina a variável de ambiente API_ALVO.
const alvo = process.env.API_ALVO || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.PORTA) || 5173,
    strictPort: true,
    proxy: {
      '/api': { target: alvo, changeOrigin: true },
      '/media': { target: alvo, changeOrigin: true },
    },
  },
})
