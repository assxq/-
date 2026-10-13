// 조회 전용 대시보드 서버. Paperclip API를 읽기(GET)로만 중계한다.
//   PAPERCLIP_URL=http://127.0.0.1:3100 PORT=3200 node server.mjs
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const TARGET = (process.env.PAPERCLIP_URL || "http://127.0.0.1:3100").replace(/\/$/, "");
const PORT = Number(process.env.PORT || 3200);
const ALLOW = /^\/api\/(companies(\/[0-9a-f-]{36}(\/(agents|issues|heartbeat-runs|live-runs|budgets\/overview|goals))?)?|issues\/[0-9a-f-]{36}\/comments)(\?[\w=&.%-]*)?$/;
const files = { "/": ["index.html", "text/html; charset=utf-8"], "/index.html": ["index.html", "text/html; charset=utf-8"] };

createServer(async (req, res) => {
  try {
    if (req.url.startsWith("/api/")) {
      if (req.method !== "GET") { res.writeHead(405).end("read-only"); return; }
      if (!ALLOW.test(req.url)) { res.writeHead(403).end("not allowed"); return; }
      const r = await fetch(TARGET + req.url, { headers: { Origin: TARGET } });
      res.writeHead(r.status, { "Content-Type": r.headers.get("content-type") || "application/json", "Cache-Control": "no-store" });
      res.end(Buffer.from(await r.arrayBuffer()));
      return;
    }
    const f = files[req.url.split("?")[0]];
    if (!f) { res.writeHead(404).end("not found"); return; }
    res.writeHead(200, { "Content-Type": f[1], "Cache-Control": "no-store" });
    res.end(await readFile(join(here, f[0])));
  } catch (e) {
    res.writeHead(502, { "Content-Type": "text/plain; charset=utf-8" }).end("Paperclip 서버에 연결하지 못했습니다: " + e.message);
  }
}).listen(PORT, "127.0.0.1", () => console.log(`대시보드: http://127.0.0.1:${PORT}  (Paperclip: ${TARGET})`));
