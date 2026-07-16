import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        escalada: {
          azul: "#0071BC",
          vermelho: "#ED1C24",
          fundo: "#F8FAFC",
          texto: "#1E293B",
        }
      },
    },
  },
  plugins: [],
};
export default config;