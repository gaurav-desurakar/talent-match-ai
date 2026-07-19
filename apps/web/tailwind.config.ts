import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172235",
        muted: "#617087",
        line: "#DCE3EA",
        canvas: "#F4F7F9",
        brand: {
          50: "#EBF8F7",
          100: "#D5F0ED",
          500: "#087F78",
          600: "#066B66",
          700: "#075A57"
        },
        navy: "#16283E",
        amber: "#B76B13"
      },
      boxShadow: {
        card: "0 1px 2px rgba(20, 37, 58, 0.06), 0 8px 24px rgba(20, 37, 58, 0.05)"
      }
    }
  },
  plugins: []
};

export default config;
