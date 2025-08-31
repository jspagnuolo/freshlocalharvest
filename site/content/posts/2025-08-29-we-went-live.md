---
title: "We went live - A static site and a few gremlins"
date: 2025-08-30T12:00:00-04:00
description: "How Fresh Local Harvest found its home on the internet—with Hugo, Cloudflare Pages, and a little friendly troubleshooting."
tags: ["launch", "behind-the-scenes"]
slug: "we-went-live"
draft: false
---

Today **Fresh Local Harvest** officially moved into its new home at **freshlocalharvest.org**. It’s fast, clean, and blissfully quiet—no servers to baby, no mystery processes humming at 3 a.m. Just a static site that gets out of the way so we can focus on the market data and the stories behind it.

Was it perfectly smooth? Of course not. But we had an extra brain in the room to keep things calm when the buttons hid and the acronyms started shouting.

## What we shipped

- A slim, accessible site built with **Hugo**.
- **Home** and **Blog** are live; a **Map** link is parked for now while the dev map UI bakes.
- Solid **SEO and security basics**: sitemaps, canonical URLs, HSTS, and tidy headers.
- A tiny **dev-only API status nudge** on the homepage, so local testing tells the truth.
- One-command workflows for local preview and production builds.
- Deployed on **Cloudflare Pages** with our domain and SSL handled end-to-end.
- Email sanity preserved: SPF, DKIM, and a fresh DMARC record (monitor mode).

If you like diff-hunting, the full changelist lives here:  
**Repo → Commits:** https://github.com/jspagnuolo/freshlocalharvest/commits/main

## The detours (aka: Where the gremlins live)

- **UI misdirection:** The dashboard kept steering us toward **Workers** instead of **Pages**. The fix was simple once we found the right tab, but it felt like pulling on a door that says “push.”
- **Hugo’s “extended” personality:** Our theme compiles SCSS, so we needed the extended build of Hugo. One setting later, the warnings turned into a green check.
- **DNS déjà vu:** Old records pointed at our cPanel host, which politely answered with a 403. We cleaned the zone, pointed both `freshlocalharvest.org` and `www` at the Pages project, and watched it snap into place.

Frustrating in the moment, oddly satisfying in the rear-view.

## Why this setup

We chose a static site for speed and reliability, **Cloudflare Pages** for zero-maintenance deploys and SSL, and a minimal theme to keep the content readable. The goal isn’t clever—it’s **fast, clear, and durable**.

## What’s next

- Wire the **Map** link to a hosted map UI as the API evolves.
- Add a tight **Content Security Policy** once our assets are steady.
- Keep a light blog cadence: short updates, real progress, no jargon detours.

Thanks for following along. If you spot anything odd—or have a farmers market story to share—say hello. We’re just getting started. 
