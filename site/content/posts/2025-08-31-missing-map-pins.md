---
title: "The Case of the Missing Map Pins"
date: 2025-08-30T12:00:00-04:00
description: "Hafter restructuring the repo and switching branches, the data that powered the map had vanished.  Learn how we restored the pins."
tags: ["launch", "behind-the-scenes"]
slug: "missing-map-pins"
draft: false
---

We started with a mystery.  
The map on our site was blank — no pins, no interactivity, just a lonely placeholder where a lively directory of farmers markets used to be. Somewhere along the way, after restructuring the repo and switching branches, the data that powered the map had vanished.  

Our goal was clear: bring the map back to life.  

---

## Step 1: Following the Breadcrumbs

The first thing we discovered was that the data folder was empty. The map had been reading from a local `markets.json` file, and that file no longer existed. No wonder the pins were gone.  

But restoring it wasn’t as simple as dropping in a backup. We’d originally ingested an Excel export from USDA, and that pipeline was now brittle. Worse, USDA had changed their website since we last worked on this — the old endpoints didn’t respond the same way.  

So we were stuck with broken ingestion code, missing data, and a map that didn’t know where to point.  

---

## Step 2: Discovering the API

After poking around the USDA’s new site, we found something promising: a proper API with documented endpoints. Better yet, their own map interface was powered by those endpoints. A quick look at the browser network tab confirmed it.  

Suddenly the path forward was obvious. Instead of relying on static Excel downloads, we could connect directly to USDA’s API.  

That came with a new challenge though: authentication. The API required a key, and calls would return 403 errors if not set up correctly.  

---

## Step 3: Wrestling with the Proxy

To keep the key secure, we built a small FastAPI proxy. The Hugo site would never talk directly to USDA — instead it would call our local API running on `http://127.0.0.1:8001/markets`.  

The proxy handled injecting the API key, normalizing the responses into Leaflet-friendly JSON, and caching results so we weren’t hammering USDA’s servers.  

This step wasn’t smooth sailing. We hit errors with:  
- Python versions (3.9 vs 3.10 vs 3.11)  
- Type hint syntax (`|` unions vs `Optional`)  
- Quoting mistakes in docstrings that caused syntax errors  
- Dependency gaps (installing `httpx[http2]` to satisfy HTTP/2 requests)  
- And plenty of 500s and 403s before the headers were just right.  

But eventually the health check came back green, the proxy relayed data, and real market listings showed up in the browser.  

---

## Step 4: The Map Lives Again

Finally, the pins reappeared. Lake Wales, Winter Haven, Auburndale — the farmers markets of Florida were back on our map.  

From there we added back navigation, tested the data export pipeline, and confirmed that the map rendered correctly both locally and on Cloudflare Pages.  

The repo was cleaned up too: `.gitignore` updated, the old Excel ingestion pipeline retired, and a `README` updated so no one would have to retrace this maze of errors again.  

---

## What We Learned

1. **One step at a time.**  
   Trying to follow a five-step plan when you get stuck on step two is frustrating. We learned to stop, fix the immediate problem, and only then move forward.  

2. **APIs beat static files.**  
   The original workflow depended on an Excel export. Switching to the official API means fresher data, fewer brittle scripts, and a more reliable site.  

3. **Good documentation matters.**  
   Having clear `README` instructions and reproducible `make` commands will save future developers (and our future selves) from hours of debugging.  

---

## Moving Forward

The map is back, but we’re not done. Next steps include:  
- Adding the search box and filters back onto the map page  
- Automating data exports so the map always stays fresh  
- Writing more lightweight posts like this one to document our bumps along the way  

What started as a frustrating debugging session ended with a stronger, more resilient project. And next time the pins go missing, we’ll know exactly where to look.
