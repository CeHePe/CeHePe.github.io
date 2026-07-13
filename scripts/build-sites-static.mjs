import { cp, mkdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dist = path.join(root, "dist");

const staticEntries = [
  "index.html",
  "styles.css",
  ".openai",
  "about",
  "home",
  "projects",
  "research",
  "templates",
];

const worker = `const fallbackOrigin = "https://cehepe.github.io";
const notFound = () => new Response("Not found", { status: 404 });

function hasExtension(pathname) {
  const name = pathname.split("/").pop() || "";
  return name.includes(".");
}

function assetRequest(request, pathname) {
  const url = new URL(request.url);
  url.pathname = pathname;
  return new Request(url, request);
}

function fallbackRequest(request, pathname) {
  const originalUrl = new URL(request.url);
  const url = new URL(pathname, fallbackOrigin);
  url.search = originalUrl.search;
  const headers = new Headers(request.headers);
  headers.delete("authorization");
  headers.delete("cookie");
  headers.delete("oai-sites-authorization");
  return new Request(url, {
    method: request.method,
    headers,
  });
}

async function fetchAsset(request, env, pathname) {
  if (env?.ASSETS?.fetch) {
    const response = await env.ASSETS.fetch(assetRequest(request, pathname));
    if (response.status !== 404) {
      return response;
    }
  }

  return fetch(fallbackRequest(request, pathname));
}

export default {
  async fetch(request, env) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method not allowed", {
        status: 405,
        headers: { Allow: "GET, HEAD" },
      });
    }

    const url = new URL(request.url);

    if (url.pathname !== "/" && !url.pathname.endsWith("/") && !hasExtension(url.pathname)) {
      url.pathname += "/";
      return Response.redirect(url.toString(), 308);
    }

    const candidate = url.pathname.endsWith("/")
      ? url.pathname + "index.html"
      : url.pathname;

    const response = await fetchAsset(request, env, candidate);
    return response.status === 404 ? notFound() : response;
  },
};
`;

await rm(dist, { recursive: true, force: true });
await mkdir(path.join(dist, "server"), { recursive: true });

for (const entry of staticEntries) {
  await cp(path.join(root, entry), path.join(dist, entry), {
    recursive: true,
    force: true,
  });
}

await writeFile(path.join(dist, "server", "index.js"), worker, "utf8");
