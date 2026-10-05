import { fileURLToPath } from "node:url";

const config = {
  plugins: {
    // Only authored UI sources contribute utilities; generated builds and
    // private export/evidence files must not change the production stylesheet.
    "@tailwindcss/postcss": {
      base: fileURLToPath(new URL("./app/", import.meta.url)),
    },
  },
};

export default config;
