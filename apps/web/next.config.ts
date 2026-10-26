import type { NextConfig } from "next";

// Extra hostnames allowed to load dev-server assets (e.g. a private preview tunnel).
// Comma-separated, set locally in .env.local; never needed in production.
const devOrigins = (process.env.DEV_ALLOWED_ORIGINS ?? "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const nextConfig: NextConfig = {
  ...(devOrigins.length ? { allowedDevOrigins: devOrigins } : {}),
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
