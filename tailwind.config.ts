import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        garmin: {
          blue: "#007cc3",
          dark: "#0b132b",
          cyan: "#00b4d8",
          neon: "#00f5d4",
          orange: "#ff7b00",
          card: "#1c2541",
        },
      },
    },
  },
  plugins: [],
};

export default config;
