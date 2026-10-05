import vinext from "vinext";
import { defineConfig } from "vite";
import { SITE_BASE_PATH } from "./site-target.mjs";

export default defineConfig({
  base: `${SITE_BASE_PATH}/`,
  plugins: [vinext()],
});
