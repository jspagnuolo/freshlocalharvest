// /api/usda?path=locSearch&lat=..&lng=..
// /api/usda?path=mktDetail&id=..

const dns = require('node:dns');
const { Agent } = require('undici');

dns.setDefaultResultOrder?.('ipv4first'); // prefer IPv4 (helps some .gov hosts)

const USDA_HOST = 'search.ams.usda.gov';
const USDA_BASE = `https://${USDA_HOST}/farmersmarkets/v1/data.svc`;

// TEMP: bypass expired TLS chain from USDA (scoped to this host only)
const insecureUSDAAgent = new Agent({
  connect: { rejectUnauthorized: false },
});

module.exports = async function handler(req, res) {
  try {
    const q = req.query || {};
    const path = String(q.path || '');
    if (!['locSearch', 'mktDetail'].includes(path)) {
      res.status(400).json({ error: "Missing or invalid 'path' (locSearch|mktDetail)" });
      return;
    }

    // Build upstream URL
    const url = new URL(`${USDA_BASE}/${path}`);
    for (const [k, v] of Object.entries(q)) {
      if (k !== 'path') url.searchParams.set(k, v);
    }

    // Fetch USDA (with our relaxed TLS dispatcher)
    const upstream = await fetch(url.toString(), {
      headers: {
        'User-Agent': 'FLH Vercel Proxy/1.0',
        'Accept': 'application/json,text/plain,*/*',
      },
      redirect: 'follow',
      // undici option supported in Node 18+ runtime on Vercel
      dispatcher: insecureUSDAAgent,
    });

    const text = await upstream.text();

    // CORS + caching headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Cache-Control', 'no-store');

    // Pass through upstream status and body (JSON or text)
    res.status(upstream.status).send(text);
  } catch (err) {
    console.error('Proxy error:', err);
    res.status(502).json({ error: 'proxy_failed', detail: String(err) });
  }
};
