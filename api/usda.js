// Vercel Serverless Function (Node.js)
// GET /api/usda?path=locSearch&lat=..&lng=..
// GET /api/usda?path=mktDetail&id=..
export default async function handler(req, res) {
  const { path, ...rest } = req.query || {};
  if (!path || !["locSearch", "mktDetail"].includes(String(path))) {
    res.status(400).json({ error: "Missing or invalid 'path' (locSearch|mktDetail)" });
    return;
  }
  const base = "https://search.ams.usda.gov/farmersmarkets/v1/data.svc";
  const url = new URL(`${base}/${path}`);
  Object.entries(rest).forEach(([k, v]) => url.searchParams.set(k, v));

  try {
    const upstream = await fetch(url.toString(), {
      headers: {
        "User-Agent": "FLH Vercel Proxy/1.0",
        "Accept": "application/json,text/plain,*/*",
      },
    });
    const text = await upstream.text();
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Cache-Control", "no-store");
    res.status(upstream.status).send(text);
  } catch (err) {
    res.status(502).json({ error: "upstream_fetch_failed", detail: String(err) });
  }
}
