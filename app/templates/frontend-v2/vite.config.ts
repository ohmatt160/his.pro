import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

const DOMAIN_LABEL_PATTERN = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;

const isValidTenantBaseDomain = (value: string) =>
  value.length <= 253 &&
  value.includes(".") &&
  value.split(".").every((label) => DOMAIN_LABEL_PATTERN.test(label));

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiProxyTarget =
    process.env.VITE_API_PROXY_TARGET ||
    env.VITE_API_PROXY_TARGET ||
    "http://localhost:8000";
  const tenantBaseDomain = (
    process.env.TENANT_BASE_DOMAIN ||
    env.TENANT_BASE_DOMAIN ||
    process.env.VITE_TENANT_BASE_DOMAIN ||
    env.VITE_TENANT_BASE_DOMAIN ||
    ""
  ).trim().toLowerCase().replace(/\.$/, "");
  const deploymentHostname =
    process.env.VERCEL_PROJECT_PRODUCTION_URL || process.env.VERCEL_URL || "";
  const publicAppOrigin = (
    process.env.PUBLIC_APP_ORIGIN ||
    env.PUBLIC_APP_ORIGIN ||
    process.env.VITE_PUBLIC_APP_ORIGIN ||
    env.VITE_PUBLIC_APP_ORIGIN ||
    (deploymentHostname ? `https://${deploymentHostname}` : "")
  ).trim();
  if (tenantBaseDomain && !isValidTenantBaseDomain(tenantBaseDomain)) {
    throw new Error("TENANT_BASE_DOMAIN must be a DNS name without a scheme or path.");
  }
  return {
    base: "/",
    build: {
      outDir: "dist",
      emptyOutDir: true,
    },
    define: {
      "import.meta.env.VITE_RESOLVED_TENANT_BASE_DOMAIN": JSON.stringify(
        tenantBaseDomain
      ),
      "import.meta.env.VITE_RESOLVED_PUBLIC_APP_ORIGIN": JSON.stringify(
        publicAppOrigin
      ),
    },
    server: {
      host: "127.0.0.1",
      port: 5174,
      strictPort: true,
      proxy: {
        "/api": {
          target: apiProxyTarget,
          changeOrigin: true,
        },
        "/auth": {
          target: apiProxyTarget,
          changeOrigin: true,
        },
        "/facilities": {
          target: apiProxyTarget,
          changeOrigin: true,
        },
      },
      hmr: {
        overlay: false,
      },
    },
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
      dedupe: ["react", "react-dom", "react/jsx-runtime", "react/jsx-dev-runtime"],
    },
  };
});
