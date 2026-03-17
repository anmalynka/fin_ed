/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#99b6d6",
        secondary: "#f5f2ed",
        tertiary: "#0f172a",
        destructive: "#e7dcdc",
        blue: {
          50: "#f8fafc",
          100: "#f1f5f9",
          400: "#7694b6",
          500: "#99b6d6",
        },
        grey: {
          50: "#ffffff",
          100: "#efe9e9",
          200: "#cbd5e1",
          300: "#404040",
          400: "#1a1a1a",
          500: "#15191d",
          900: "#0f172a",
        },
        brand: {
          border: "#6b7280",
          positive: "#1E8257",
          negative: "#A45951",
        }
      },
      borderRadius: {
        'xs': '4px',
        's': '8px',
        'm': '12px',
        'l': '16px',
        'xl': '20px',
        'xxl': '24px',
      }
    },
  },
  plugins: [],
}
