// /api/usda?path=locSearch&lat=..&lng=..
// /api/usda?path=mktDetail&id=..
import dns from "node:dns";
import { Agent } from "undici";

dns.setDefaultResultOrder?.("ipv4first"); // be IPv4-friendly

const USDA_HOST = "search.ams.usda.gov";
const USDA_BASE = `https://${USDA_HOST}/farmersmarkets/v1/data.svc`;

// Insecure agent ONLY for USDA host (temporary: their cert is expired)
const insecureUSDAAgent = new Agent({
  connect: { rejectUnauthorized: false },
});

export default async function handler(req, res) {
  try {
    const { path, ...rest } = req.query || {};
    if (!path || !["locSearch", "mktDetail"].includes(String(path))) {
      res.status(400).json({ error: "Missing or invalid 'path' (locSearch|mktDetail)" });
      return;
    }

    // Build upstream URL
    const url = new URL(`${USDA_BASE}/${path}`);
    Object.entries(rest).forEach(([k, v]) => url.searchParams.set(k, v));

    // Use insecure dispatcher ONLY for this host to bypass the expired cert
    const dispatcher = url.hostname === USDA_HOST ? insecureUSDAAgent : undefined;

    const upstream = await fetch(url.toString(), {
      headers: {
        "User-Agent": "FLH Vercel Proxy/1.0",
        "Accept": "application/json,text/plain,*/*",
      },
      redirect: "follow",
      // @ts-ignore — undici option supported in Node 18+
      dispatcher,
    });

    const text = await upstream.text();
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Cache-Control", "no-store");

    if (!upstream.ok) {
      // bubble USDA errors so we can see them
      res.status(upstream.status).send(text);
      return;
    }

    const ct = upstream.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      res.status(200).send(text);
    } else {
      res.setHeader("Content-Type", ct || "application/json");
      res.status(200).send(text);
    }
  } catch (err) {
    console.error("Proxy error:", err);
    res.status(502).json({ error: "upstream_fetch_failed", detail: String(err) });
  }
}
