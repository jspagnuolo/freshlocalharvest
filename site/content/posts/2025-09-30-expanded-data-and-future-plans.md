---
title: "Expanded Data and Future plans"
date: 2025-09-29T18:00:00-04:00
description: "Planning a directions feature for the Fresh Local Harvest map while we scout free, community-friendly data sources for hours, phones, and more."
tags: ["project-notes", "map", "search", "open-data"]
slug: "data-expaneded-future-plans"
draft: false
---

The map keeps getting better. Over the past week we ingested five USDA datasets—farmers markets, CSAs, food hubs, on-farm markets, and agritourism listings—bringing **27,383** locations into a single search experience. Zip and city centroids work across every category, type filtering is instant, and the state search is back on track after we taught the parser to ignore “USA” in the address tail.

Now we’re lining up the next round of polish: **a “Get directions” link on every result and map pin.** It’s a simple, familiar action and the clearest path to enjoying fresh food in real life.

## Where we are today

- One dataset pipeline, many USDA sources—all refreshed with `make run`.
- A front-end filter bar that lets you search by city, state, ZIP, keyword, and type.
- Radius searches for both ZIP codes *(30 miles)* and city centroids, plus geolocation-powered “near me” results.
- Each result card highlights the program badges we know about (SNAP, WIC, incentives, etc.).

## What’s next: Directions on tap

The plan is straightforward:

1. **Wire in the “Get directions” link** pointing at the user’s preferred mapping app. We’ll start with a universal Google Maps URL (with latitude/longitude and the listing name) and expose it on the result card and in the popup.
2. **Gracefully handle missing coordinates.** Every record we kept already has valid lat/lon, but we’ll still guard against edge cases.
3. **Respect mobile users.** The link should open the native app when possible and fall back to the browser on desktop.

This keeps our interface lean, while giving visitors a one-click path from research to action.

## Finding hours without blowing the budget

Because this is an open-source, not-for-profit project, the commercial Places APIs aren’t an option so we’re exploring free or community-friendly paths for richer details:

- **Open data portals** (state agriculture departments, municipal open data, USDA sub-programs).
- **Crowdsourced directories** like OpenStreetMap, which may provide hours or phone numbers when volunteers have added them.

We’ll prototype any new data source in a small batch first to make sure it’s reliable, up-to-date, and compliant with usage rights.



