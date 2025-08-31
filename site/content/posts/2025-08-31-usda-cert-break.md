# USDA Certificate Issue Stalls Our Progress

Today we spent nearly 8 hours trying to set up our daily data pipeline for **Fresh Local Harvest**, which pulls U.S. farmers market information from the USDA Local Food Directory. Our goal was to automate updates so the site always reflects the latest markets.

## What Happened
No matter how we connected — through Cloudflare, HostGator, or Vercel — the USDA API calls failed. At first, it looked like a coding or configuration issue on our end. But after testing every angle, we discovered the real problem:  

👉 The USDA API endpoint is serving an **expired/invalid SSL certificate**.  

This means connections to their servers can’t be trusted, and automated systems (like ours) block the calls for security reasons.

## Our Decision
Rather than burn more time, we’ve paused the project until USDA fixes their certificate. We’ve:

- Disabled the automated workflow.  
- Parked the repo in a clean state.  
- Documented the issue and reached out to USDA support.  

## Next Steps
Once USDA updates their certificate, we’ll pick up right where we left off. At that point, we’ll run everything through **Cloudflare Workers** to keep our stack simple and secure.

## Reflection
This session was a reminder that patience is part of the process. Even with trial and error, the key is knowing when the problem isn’t yours to solve. For now, we wait — and once USDA resolves the certificate issue, we’ll be ready to continue.

*Posted: August 31, 2025*
