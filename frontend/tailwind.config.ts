/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        atlas: {
          gold: "#D4AF37",
          dark: "#0F1419",
          panel: "#1A2332",
        },
      },
    },
  },
  plugins: [],
};
