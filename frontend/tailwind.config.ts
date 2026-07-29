/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#030304",
        surface: "#08080b",
        panel: "#0f0f14",
        elevated: "#16161d",
        border: "#22222c",
        muted: "#6b6b7b",
        gold: {
          DEFAULT: "#e8c547",
          dim: "#9a7b2f",
          glow: "#f5d76e",
        },
        buy: "#34d399",
        sell: "#f87171",
        wait: "#71717a",
      },
      fontFamily: {
        display: ["Syne", "system-ui", "sans-serif"],
        sans: ["DM Sans", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 40px -8px rgba(232, 197, 71, 0.25)",
        panel: "0 4px 24px -4px rgba(0, 0, 0, 0.6)",
      },
      backgroundImage: {
        grid: `linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)`,
        "radial-gold": "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(232,197,71,0.12), transparent)",
      },
      backgroundSize: {
        grid: "48px 48px",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6,  1) infinite",
        shimmer: "shimmer 2s linear infinite",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};
