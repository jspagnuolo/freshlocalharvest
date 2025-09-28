// File: functions/user-location.js
export const onRequestGet = async ({ request }) => {
  const cf = request.cf || {};

  const latitude = cf.latitude != null ? Number(cf.latitude) : null;
  const longitude = cf.longitude != null ? Number(cf.longitude) : null;
  const city = cf.city || null;
  const region = cf.region || null;
  const country = cf.country || null;
  const postalCode = cf.postalCode || null;
  const metroCode = cf.metroCode || null;

  const payload = {
    latitude: Number.isFinite(latitude) ? latitude : null,
    longitude: Number.isFinite(longitude) ? longitude : null,
    city,
    region,
    country,
    postalCode,
    metroCode,
    source: 'cloudflare-headers'
  };

  return new Response(JSON.stringify(payload), {
    headers: {
      'content-type': 'application/json',
      'cache-control': 'no-store, max-age=0'
    }
  });
};
