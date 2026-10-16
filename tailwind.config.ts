import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-roboto)", "Roboto", "system-ui", "-apple-system", "sans-serif"],
      },
      colors: {
        background: "var(--md-sys-color-background)",
        foreground: "var(--md-sys-color-on-background)",
        // Material Design 3 semantic color tokens
        md: {
          sys: {
            color: {
              primary: "var(--md-sys-color-primary)",
              "on-primary": "var(--md-sys-color-on-primary)",
              "primary-container": "var(--md-sys-color-primary-container)",
              "on-primary-container": "var(--md-sys-color-on-primary-container)",
              secondary: "var(--md-sys-color-secondary)",
              "on-secondary": "var(--md-sys-color-on-secondary)",
              "secondary-container": "var(--md-sys-color-secondary-container)",
              "on-secondary-container": "var(--md-sys-color-on-secondary-container)",
              tertiary: "var(--md-sys-color-tertiary)",
              "on-tertiary": "var(--md-sys-color-on-tertiary)",
              "tertiary-container": "var(--md-sys-color-tertiary-container)",
              "on-tertiary-container": "var(--md-sys-color-on-tertiary-container)",
              error: "var(--md-sys-color-error)",
              "on-error": "var(--md-sys-color-on-error)",
              "error-container": "var(--md-sys-color-error-container)",
              "on-error-container": "var(--md-sys-color-on-error-container)",
              surface: "var(--md-sys-color-surface)",
              "surface-dim": "var(--md-sys-color-surface-dim)",
              "surface-bright": "var(--md-sys-color-surface-bright)",
              "surface-container-lowest": "var(--md-sys-color-surface-container-lowest)",
              "surface-container-low": "var(--md-sys-color-surface-container-low)",
              "surface-container": "var(--md-sys-color-surface-container)",
              "surface-container-high": "var(--md-sys-color-surface-container-high)",
              "surface-container-highest": "var(--md-sys-color-surface-container-highest)",
              "on-surface": "var(--md-sys-color-on-surface)",
              "on-surface-variant": "var(--md-sys-color-on-surface-variant)",
              outline: "var(--md-sys-color-outline)",
              "outline-variant": "var(--md-sys-color-outline-variant)",
            },
          },
        },
      },
      boxShadow: {
        "elevation-1": "0 1px 3px 1px rgba(0,0,0,0.15), 0 1px 2px 0 rgba(0,0,0,0.30)",
        "elevation-2": "0 2px 6px 2px rgba(0,0,0,0.15), 0 1px 2px 0 rgba(0,0,0,0.30)",
        "elevation-3": "0 4px 8px 3px rgba(0,0,0,0.15), 0 1px 3px 0 rgba(0,0,0,0.30)",
        "elevation-4": "0 6px 10px 4px rgba(0,0,0,0.15), 0 2px 3px 0 rgba(0,0,0,0.30)",
        "elevation-5": "0 8px 12px 6px rgba(0,0,0,0.15), 0 4px 4px 0 rgba(0,0,0,0.30)",
      },
      borderRadius: {
        "4xl": "28px",
      },
    },
  },
  plugins: [],
};

export default config;
