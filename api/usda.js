// /api/usda?path=locSearch&lat=..&lng=..
// /api/usda?path=mktDetail&id=..
import dns from "node:dns";
dns.setDefaultResultOrder?.("ipv4first"); // prefer IPv4 (sometimes helps on .gov)

const ORIGINS = [
  "https://search.ams.usda.gov/farmersmarkets/v1/data.svc",
  "http://search.ams.usda.gov/farmersmarkets/v1/data.svc" // fallback if HTTPS handshake is fussy
];

export default async function handler(req, res) {
  try {
    const { path, ...rest } = req.query || {};
    if (!path || !["locSearch", "mktDetail"].includes(String(path))) {
      res.status(400).json({ error: "Missing or invalid 'path' (locSearch|mktDetail)" });
      return;
    }

    // Build upstream URLs (try HTTPS, then HTTP)
    const urls = ORIGINS.map(base => {
      const u = new URL(`${base}/${path}`);
      Object.entries(rest).forEach(([k, v]) => u.searchParams.set(k, v));
      return u.toString();
    });

    let lastErr = null;
    for (const u of urls) {
      try {
        const upstream = await fetch(u, {
          headers: {
            "User-Agent": "FLH Vercel Proxy/1.0",
            "Accept": "application/json,text/plain,*/*"
          },
          redirect: "follow"
        });
        const text = await upstream.text(); // read once
        if (!upstream.ok) {
          // bubble upstream error (e.g., 403) so we can see it in job logs
          res.setHeader("Access-Control-Allow-Origin", "*");
          res.setHeader("Cache-Control", "no-store");
          res.status(upstream.status).send(text);
          return;
        }
        // try to return JSON; if not JSON, return text as-is
        res.setHeader("Access-Control-Allow-Origin", "*");
        res.setHeader("Cache-Control", "no-store");
        const ct = upstream.headers.get("content-type") || "";
        if (ct.includes("application/json")) {
          res.status(200).send(text);
        } else {
          res.setHeader("Content-Type", ct || "application/json");
          res.status(200).send(text);
        }
        return;
      } catch (e) {
        lastErr = e;
        console.error("Upstream fetch failed for", u, e);
        // try next origin
      }
    }

    // All attempts failed
    res.status(502).json({ error: "upstream_fetch_failed", detail: String(lastErr) });
  } catch (err) {
    console.error("Proxy error:", err);
    res.status(500).json({ error: "proxy_failed", detail: String(err) });
  }
}
