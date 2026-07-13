import { cp, mkdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dist = path.join(root, "dist");

const staticEntries = [
  "index.html",
  "styles.css",
  "about",
  "home",
  "projects",
  "research",
  "templates",
];

const worker = `const notFound = () => new Response("Not found", { status: 404 });

function hasExtension(pathname) {
  const name = pathname.split("/").pop() || "";
  return name.includes(".");
}

function assetRequest(request, pathname) {
  const url = new URL(request.url);
  url.pathname = pathname;
  return new Request(url, request);
}

export default {
  async fetch(request, env) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method not allowed", {
        status: 405,
        headers: { Allow: "GET, HEAD" },
      });
    }

    if (!env?.ASSETS?.fetch) {
      return notFound();
    }

    const url = new URL(request.url);

    if (url.pathname !== "/" && !url.pathname.endsWith("/") && !hasExtension(url.pathname)) {
      url.pathname += "/";
      return Response.redirect(url.toString(), 308);
    }

    const candidate = url.pathname.endsWith("/")
      ? url.pathname + "index.html"
      : url.pathname;

    const response = await env.ASSETS.fetch(assetRequest(request, candidate));
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
