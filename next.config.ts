import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  // vinext 0.0.50 static-export prerendering fetches unprefixed routes.
  // The Vite asset base and relative document URLs provide the hosted mount.
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
