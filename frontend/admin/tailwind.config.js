/**
 * STYLING CONVENTION:
 * - Use Tailwind utility classes with `app-*` design tokens for all new code
 * - Use CSS Modules only for complex animations or page-specific layouts
 * - Use `cn()` from @/lib/utils for conditional class merging
 * - Do NOT use `clsx()` directly — always use `cn()` which wraps clsx + twMerge
 */

/** @type {import('tailwindcss').Config} */
const config = {
  content: ['./src/**/*.{js,jsx,mdx}'],
  theme: {
    extend: {
      colors: {
        app: {
          bg: '#efeff0',
          panel: '#ffffff',
          border: '#dfdfe2',
          text: '#22252b',
          muted: '#878b93',
          sidebar: '#25272b',
          sidebarSoft: '#555860',
          success: '#2f9b4b',
          danger: '#cf4444',
          card: '#f4f3f1',
          'text-dark': '#2d2d2d',
          'text-secondary': '#7e7e7e',
          divider: '#e0dedb',
          'sidebar-text': '#d2d0ca',
          'badge-china': '#f2e5c2',
          'badge-china-text': '#5c4a17',
          'text-darker': '#3d3d3d',
          'border-soft': '#f0f0f0',
          accent: '#429700',
          'accent-danger': '#aa2d2d',
        },
      },
      boxShadow: {
        soft: '0 8px 24px rgba(18, 28, 45, 0.06)',
      },
      fontFamily: {
        sans: [
          'Inter',
          '"Segoe UI"',
          '"SF Pro Text"',
          '"Helvetica Neue"',
          'sans-serif',
        ],
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        fadeIn: 'fadeIn 220ms ease-out',
      },
    },
  },
  plugins: [],
};

module.exports = config;
