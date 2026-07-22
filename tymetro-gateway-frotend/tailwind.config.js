/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // === 靜態色（不隨主題切換）===
        primary: {
          50: "#f3f6fb",
          100: "#e4ebf5",
          200: "#ceddef",
          300: "#adc6e3",
          400: "#85a9d5",
          500: "#688dc9",
          600: "#5575bb",
          700: "#4a64ab",
          800: "#405189",
          900: "#384770",
          950: "#262d45",
        },
        secondary: {
          50: "#D6F6FF",
          100: "#C3F3FF",
          500: "#00ACC1",
          500: "#006B79",
        },
        muted: {
          50: "#f8fafc",
          100: "#f1f5f9",
          200: "#e2e8f0",
          300: "#cad5e2",
          400: "#90a1b9",
          500: "#62748e",
          600: "#45556c",
          700: "#314158",
          800: "#1d293d",
          900: "#0f172b",
          950: "#020618",
        },
        success: {
          DEFAULT: "rgb(var(--success) / <alpha-value>)", // 可用 bg-success、bg-success/10
          100: "#e3f5ed",
          500: "#30af98",
        },
        warning: {
          DEFAULT: "rgb(var(--warning) / <alpha-value>)",
          100: "#fff7e6",
          500: "#FF9800",
        },
        error: {
          DEFAULT: "rgb(var(--error) / <alpha-value>)",
          100: "#fde9e6",
          500: "#ff5541",
        },
        danger: {
          DEFAULT: "rgb(var(--danger) / <alpha-value>)",
          50: "#FDEDF1",
          100: "#FBDAE3",
          500: "#DE287A",
        },
        info: {
          DEFAULT: "rgb(var(--info) / <alpha-value>)",
          100: "##ffffff",
          500: "#2196f3",
        },
        default: {
          DEFAULT: "rgb(var(--default) / <alpha-value>)",
          100: "#e4ebf5",
          500: "#688dc9",
        },
        // 其他語義/變數色
        bg: "rgb(var(--bg) / <alpha-value>)",
        text: "rgb(var(--fg) / <alpha-value>)",
        card: "rgb(var(--card) / <alpha-value>)",
        border: "rgb(var(--border) / <alpha-value>)",
        theme: "rgb(var(--primary) / <alpha-value>)",
        bgSecondary: "rgb(var(--bg-secondary) / <alpha-value>)",
        input: "rgb(var(--input) / <alpha-value>)",
        ring: "rgb(var(--ring) / <alpha-value>)",
        primaryBrand: "rgb(var(--primary-brand) / <alpha-value>)",
      },
      fontSize: {
        md: "0.9375rem",
      },
    },
  },
  plugins: [],
};
