---
title: "How We Turned a Prototype into a Useful Market Map (with Codex)"
date: 2025-09-28T18:00:00-04:00
description: "A behind-the-scenes look at how we simplified the project, rebuilt the map, and made search actually helpful—thanks to Codex inside VS Code."
tags: ["project-notes", "map", "search", "ai"]
slug: "prototype-to-useful-map-with-codex"
draft: false
---

We’ve been quietly reshaping Fresh Local Harvest over the past few weeks. The goal was simple: **make it easier to find nearby farmers markets**—without asking you to learn a new interface or guess the right search terms. Along the way we moved our workflow into **Codex inside VS Code**, which turned out to be exactly the nudge we needed to finish the job.

## The short version

- We removed a fragile detour that depended on a flaky government API and **committed to a single, reliable Excel → website path**.
- We **enriched the data** so the map understands cities, states, and ZIP codes the way people actually search.
- The map now **shows results near you**, and **pins display useful details** (name, address, programs like SNAP/WIC).
- It all **deploys cleanly** to Cloudflare Pages when we push changes.

## Why we changed course

Earlier, the project tried to do two things at once: fetch live data from a government API _and_ process spreadsheets locally. That split left both halves half-done. We decided to focus on one path—the **local spreadsheet method**—because it’s dependable and gives us control over data quality.

## What changed (in human terms)

- **Cleaner data = better search.** We standardized city/state/ZIP info and added simple “centers” for cities and ZIP codes. That lets the map search “Tampa” or “33625” and show **nearby markets within a short drive** instead of guessing.
- **Friendlier map.** On desktop, the map and results list sit side-by-side; on phones, the map is front and center with a tidy list beneath. Popups include what matters most: name, address, and key programs (like SNAP).
- **Near me.** When you land on the page, the map uses Cloudflare’s privacy-friendly location headers to **center near your area** and list nearby markets. No sign-ins, no trackers—just a better starting point.

## Why Codex (inside VS Code) helped

We’ve done plenty of “copy/paste into a chat” in the past. It works, but it can be slow and scattershot. **Codex inside VS Code** lives with the codebase, so it can see related files at once and suggest changes that **fit the whole project**, not just a snippet. That meant we could streamline the data flow, update the map, and tweak copy and layout in one cohesive push instead of a dozen tiny ones.

## What you can do now

- **Type a city or ZIP** and see the nearby markets, not random name matches.
- **Click any pin** to get the essentials (address, programs).
- **Open the site on your phone**—the map now behaves like a proper mobile experience.

## What’s next

1. **Move the map to the homepage.** It’s the heart of the site—let’s put it front-and-center so visitors can search right away.
2. **Enrich the dataset beyond farmers markets.** We’ll explore official sources for **CSA farms, food hubs, farm stands**, and other places to find local produce. The goal: one map, many pathways to fresh food.
3. **Practical details research.** We’ll look for trustworthy sources to add **hours of operation and contact info**.


