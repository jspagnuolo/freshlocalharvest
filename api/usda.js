// /api/usda?path=locSearch&lat=..&lng=..
// /api/usda?path=mktDetail&id=..

const https = require('node:https');
const http = require('node:http');
const { URL } = require('node:url');

const USDA_HOST = 'search.ams.usda.gov';
const USDA_BASE = `https://${USDA_HOST}/farmersmarkets/v1/data.svc`;

// TEMP: bypass USDA's incomplete cert chain (scoped to this host only)
const insecureUSDAAgent = new https.Agent({ rejectUnauthorized: false });

function fetchViaNode(u) {
  return new Promise((resolve, reject) => {
    const url = new URL(u);
    const isHttps = url.protocol === 'https:';
    const mod = isHttps ? https : http;

    const options = {
      method: 'GET',
      headers: {
        'User-Agent': 'FLH Vercel Proxy/1.0',
        'Accept': 'application/json,text/plain,*/*',
      },
      // RELAX TLS ONLY for USDA host; everything else remains strict
      agent: (isHttps && url.hostname === USDA_HOST) ? insecureUSDAAgent : undefined,
    };

    const req = mod.request(url, options, (res) => {
      const chunks = [];
      res.on('data', (d) => chunks.push(d));
      res.on('end', () => {
        const body = Buffer.concat(chunks).toString('utf8');
        resolve({
          status: res.statusCode || 502,
          headers: res.headers,
          body,
        });
      });
    });

    req.on('error', reject);
    req.end();
  });
}

module.exports = async function handler(req, res) {
  try {
    const q = req.query || {};
    const path = String(q.path || '');

    if (!['locSearch', 'mktDetail'].includes(path)) {
      res.status(400).json({ error: "Missing or invalid 'path' (locSearch|mktDetail)" });
      return;
    }

    // Build upstream USDA URL
    const upstream = new URL(`${USDA_BASE}/${path}`);
    for (const [k, v] of Object.entries(q)) {
      if (k !== 'path') upstream.searchParams.set(k, v);
    }

    const { status, headers, body } = await fetchViaNode(upstream.toString());

    // CORS + no-store
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Cache-Control', 'no-store');

    // Preserve content-type if given; default to JSON
    res.setHeader('Content-Type', headers['content-type'] || 'application/json');

    res.status(status).send(body);
  } catch (err) {
    console.error('Proxy error:', err);
    res.status(502).json({ error: 'proxy_failed', detail: String(err) });
  }
};
