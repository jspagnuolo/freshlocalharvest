---
title: "Chasing Clean Data (and Catching Most of It)"
date: 2025-08-20T14:15:00-04:00
description: "Where our farmers market data comes from, how we shaped it, and the small victories that make it trustworthy."
tags: ["data", "behind-the-scenes", "markets"]
slug: "data-journey-markets"
draft: false
---

Data hunts rarely start glamorous. Ours began with a simple question: **where do we find a reliable, national list of farmers markets?** Then came spreadsheets, acronyms, and a lot of “huh, that’s interesting.”

## The short version

We sourced a national directory, normalized it into a clean, portable database, added guardrails for trust, and exposed it via an API that’s fast enough for maps and simple enough for people. Not perfect yet—but solid, explainable, and built to improve.

## Where the data comes from

We started with a publicly available farmers market directory (think: the big national one). It’s broad, reasonably current, and—like all real-world datasets—a little messy around the edges. Our first pass brought in **~7,000 markets** with fields like name, city, state, ZIP, latitude/longitude, phone, website, and whether the market **accepts SNAP**.

## What “clean” means to us (for now)

- **Consistent columns**: markets get the same shape—name, city, state, zip, lat, lon, website, phone, accepts_snap—so the API and the UI can be boring (in the best way).
- **Stable IDs**: if a source doesn’t provide one, we deterministically generate a **market_id** from key fields (name/city/state/zip/lat/lon). That keeps links stable even as we improve details later.
- **Duplicates & weirdness**: we flag likely dupes, watch for out-of-bounds coordinates, and keep an eye on suspicious ZIP/state combos.
- **SNAP awareness**: we track `accepts_snap` now, with room to grow into richer EBT details as better sources come online.

## How the API thinks

We designed endpoints around **how people actually search**:

- **By name or city** when you already know what you want.
- **By state** for broader browsing.
- **By map viewport** (a bounding box) so we can fetch exactly what’s on screen without hammering the server.
- **By distance** (lat/lon + radius) for “near me” use cases.
- **Limit/offset** so pagination is predictable and fast.

The result: snappy queries that hold up well as we scale.

## Quality checks (aka: don’t ship vibes)

- **Smoke tests** ping health and a handful of queries.
- **Spot checks** for outliers: coordinates near (0,0), oceans, or states that don’t match.
- **Link hygiene**: websites that look parked or phones that look… creative… get flagged for review later.
- **Reproducibility**: all of this is scripted, so updates don’t become a game of telephone.

## Why we chose SQLite first

Because **it’s perfect for this stage**: a single file, easy to ship and diff, and more than fast enough for our queries. When we need more horsepower, we can move up the stack without changing how the API feels.

## What we learned (and will keep doing)

- **Trust is a process**. Start with one good source, normalize it, and layer improvements.
- **IDs matter**. Stable IDs unlock bookmarks, shares, and updates without breaking links.
- **Maps need math**. Viewport and radius queries make the UI feel instant—and keep costs down.
- **Small steps win**. A steady loop of ingest → normalize → test beats “big bang” imports every time.

## What’s next

- **Enrichment**: expand EBT/SNAP details and add more attributes people care about (hours, seasonality, product focus).
- **Corrections**: invite the community to submit fixes and verify them quickly.
- **Freshness**: set a regular refresh cadence and make it visible on the site.
- **Observability**: light metrics on API usage so we can spot hot spots and weird spikes early.

If you want to peek behind the curtain, here’s the commit history for this work (file adds, schema notes, and API tweaks included):  
**Repo → Commits:** https://github.com/jspagnuolo/freshlocalharvest/commits/main

We’ll keep polishing. In the meantime, the data’s good enough to be useful—and that’s the whole point.
