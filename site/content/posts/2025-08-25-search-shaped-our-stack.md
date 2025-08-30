---
title: "What the Search Data Told Us (and Why We Listened)"
date: 2025-08-25T17:30:00-04:00
description: "How real-world search patterns shaped our tech choices, rollout plan, and the way we’ll cover farmer’s markets over time."
tags: ["strategy", "search", "planning", "stack"]
slug: "search-shaped-our-stack"
draft: false
---

We looked at how people actually search for farmers markets and, surprise: the internet behaves like a Saturday morning. There are early birds, there are seasonal stampedes, and “near me” rules the day. That little bit of reality-check shaped our stack and our rollout plan more than any fancy diagram.

## What we looked at

- **Seasonality**: peaks around spring openings, summer abundance, and the fall harvest (pumpkins do numbers).  
- **Weekly rhythm**: predictable bumps late week and Saturday mornings.  
- **Geography**: sunbelt states (hello, Florida) show longer seasons and higher baseline interest than colder states (hi, Ohio), but both spike when markets open.  
- **Intent**: “farmers market near me,” “hours,” “open now,” and “SNAP/EBT” show up a lot—short, local, urgent.

Takeaway: we’re building for **spikes**, **mobile**, and **quick answers**.

## How that shaped the stack

- **Static-first website**: We serve almost everything as cached HTML from the edge. No servers to melt when a Saturday surge rolls in.  
- **Tiny API for the hard parts**: Search by viewport, radius, or filters (like SNAP) is dynamic—but small and fast—so we can scale the heavy lifting without turning every page into a live computation.  
- **Edge distribution**: Cloudflare Pages/CDN keeps us snappy, even when everyone is checking tomatoes at once.  
- **Simple data store (for now)**: SQLite powers the early API. It’s enough for today’s queries and portable for tomorrow’s migration.  
- **Boring by design**: Hugo pages, clean links, no mystery frameworks. The goal is **fast answers**, not a science project.

## Why this helps real people

- **Shoppers** get quick, local results on a phone with weak reception in a parking lot.  
- **Market managers** don’t lose traffic during peak season; edge caching and a small API are resilient under load.  
- **Communities** see SNAP/EBT information up front, in plain language.

## Standardizing coverage over time

Data wants a plan. Here’s ours:

- **One schema, everywhere**: name, city, state, ZIP, lat/lon, phone, website, `accepts_snap`, and a **stable market ID** so bookmarks and updates don’t break.  
- **Repeatable ingest**: same playbook each refresh—pull, normalize, flag weirdness, publish.  
- **Geographic sweep**: publish **state-level indexes** and **city landing pages** as we go, so people can browse even without searching.  
- **Quality gates**: out-of-bounds coordinates, suspicious ZIP/state combos, parked domains, and placeholder phones get flagged for review.  
- **Changelog in public**: small, frequent releases beat “big bang” updates. You’ll see progress roll across the map.

## SEO choices (guided by search intent)

- **Clean, stable URLs** for states and cities.  
- **Fast pages first**: no flicker, no cookie walls, no heavy bundles.  
- **Helpful snippets**: opening hours and SNAP where we have them; no clickbait.  
- **Canonical + sitemap hygiene** to keep crawlers happy as coverage expands.

## How we’ll measure ourselves

- **Time-to-answer**: how fast a person can land, scan, and decide.  
- **Coverage**: % of markets verified, % with SNAP info, freshness age.  
- **Reliability**: uptime during weekend surges, error rates on map/radius queries.  
- **Feedback**: real corrections from real people, merged quickly.

## Decisions we’re not overthinking (yet)

- A heavyweight database can wait until the API says it needs one.  
- Fancy ML for deduping data can wait until simple rules stop working.  
- A complex app shell can wait until users need features the static site can’t deliver.

We’ll keep reading the signals—seasonal curves, “near me” intent, SNAP interest—and let that guide what we build next. If the pattern changes, so will we. That’s the fun part.

If you’re curious about the nuts and bolts behind these choices, the commit history tells the tale—one small, reversible step at a time.
