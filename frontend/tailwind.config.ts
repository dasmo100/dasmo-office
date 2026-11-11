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
        dasmo: {
          dark: "#0b0f19",
          card: "#111827",
          border: "#1f2937",
          accent: "#6366f1",
          success: "#10b981",
          warning: "#f59e0b",
        },
      },
      aspectRatio: {
        "9/16": "9 / 16",
      },
    },
  },
  plugins: [],
};
export default config;
