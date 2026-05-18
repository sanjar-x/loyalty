import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.js'],
    globals: true,
  },
  resolve: {
    // FSD alias resolution — строго на src/{layer}/. Никаких repo-root
    // fallback'ов: миграция завершена, fallback бы тихо подцепил мусор из
    // корня (openapi.json, scripts/, tmp/) и обошёл бы ESLint-проверки на
    // несуществующие пути.
    alias: [
      { find: /^@\/shared\/(.*)$/, replacement: path.resolve(__dirname, 'src/shared/$1') },
      { find: /^@\/entities\/(.*)$/, replacement: path.resolve(__dirname, 'src/entities/$1') },
      { find: /^@\/features\/(.*)$/, replacement: path.resolve(__dirname, 'src/features/$1') },
      { find: /^@\/widgets\/(.*)$/, replacement: path.resolve(__dirname, 'src/widgets/$1') },
      { find: /^@\/app\/(.*)$/, replacement: path.resolve(__dirname, 'src/app/$1') },
    ],
  },
});
