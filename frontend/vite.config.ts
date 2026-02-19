import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import http from "node:http";

/** Silent proxy plugin — forwards /api and /health to the backend,
 *  returns a clean 502 JSON when the backend is unreachable instead
 *  of flooding the terminal with ECONNREFUSED stack traces. */
function silentApiProxy(target: string): Plugin {
  return {
    name: "silent-api-proxy",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!req.url?.startsWith("/api") && !req.url?.startsWith("/health")) {
          return next();
        }

        // Buffer the full request body before forwarding so that
        // Content-Length is accurate for multipart/file uploads.
        const chunks: Buffer[] = [];
        req.on("data", (chunk: Buffer) => chunks.push(chunk));
        req.on("end", () => {
          const body = Buffer.concat(chunks);
          const url = new URL(req.url!, target);
          const fwdHeaders = { ...req.headers, host: url.host };
          // Ensure Content-Length matches the actual buffered body
          fwdHeaders["content-length"] = String(body.length);

          const proxyReq = http.request(
            url,
            {
              method: req.method,
              headers: fwdHeaders,
            },
            (proxyRes) => {
              res.writeHead(proxyRes.statusCode ?? 502, proxyRes.headers);
              proxyRes.pipe(res);
            },
          );

          proxyReq.on("error", () => {
            if (!res.headersSent) {
              res.writeHead(502, { "Content-Type": "application/json" });
              res.end(JSON.stringify({ error: "API unavailable" }));
            }
          });

          proxyReq.end(body);
        });
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), silentApiProxy("http://localhost:8000")],
  server: {
    port: 5173,
  },
});
