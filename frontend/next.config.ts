import type { NextConfig } from "next";

import { allowedDevOriginsFromAppOrigin } from "./src/lib/allowed-dev-origin";

const nextConfig: NextConfig = {
  reactCompiler: true,
  skipTrailingSlashRedirect: true,
  ...(process.env.NODE_ENV === "development"
    ? { allowedDevOrigins: allowedDevOriginsFromAppOrigin(process.env.SIA_APP_ORIGIN) }
    : {}),
};

export default nextConfig;
