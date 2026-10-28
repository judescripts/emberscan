import type { NextConfig } from "next";

// Extra hostnames allowed to load dev-server assets (e.g. a private preview tunnel).
// Comma-separated, set locally in .env.local; never needed in production.
const devOrigins = (process.env.DEV_ALLOWED_ORIGINS ?? "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const nextConfig: NextConfig = {
  ...(devOrigins.length ? { allowedDevOrigins: devOrigins } : {}),
  // Lets a production build run beside `next dev` (e.g. NEXT_DIST_DIR=.next-build npm run build).
  ...(process.env.NEXT_DIST_DIR ? { distDir: process.env.NEXT_DIST_DIR } : {}),
  // PGlite loads its WASM and data files from its package directory at runtime.
  serverExternalPackages: ["@electric-sql/pglite"],
  // No Next.js badge in the corner of the dev server (it shows up in screen recordings).
  devIndicators: false,
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
