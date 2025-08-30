---
title: "Why Fresh Local Harvest (and Who It’s For)"
date: 2025-08-10T16:20:00-04:00
description: "A simple site for finding farmers markets—and a gentle blueprint for building with AI even if you don’t write code."
tags: ["mission", "community", "ai", "makers"]
slug: "why-and-who"
draft: false
---

Fresh food is a local story. It’s neighbors with tables, growers with early mornings, and a quick “what’s good today?” across a pile of tomatoes. **Fresh Local Harvest** exists to make that connection easier—and to show that you don’t need to be a programmer to build something useful with AI at your side.

## Why we’re doing this

Because finding **reliable, current info** about farmers markets shouldn’t require detective work. We wanted a place that’s **fast**, **clean**, and **up-to-date**—just the essentials: what’s nearby, when it runs, how to reach them, and whether they accept SNAP.

And honestly? We also wanted to prove a point: with the right scaffolding, **non-developers can ship software**. Not prototype. **Ship.**

## Who this helps

**People looking for markets**  
You get a simple site that loads quickly and respects your time. We won’t bury you in pop-ups. We’ll show you what you need and let you move on with your day.

**Market managers & growers**  
The easier it is for people to find you, the better your Saturdays go. As we add enrichment and lightweight update flows, you’ll be able to keep your info fresh without a tech marathon.

**Community & public health folks**  
When fresh food is easier to find—especially with **SNAP** acceptance—everybody wins. We’re aiming for clarity over cleverness.

**Curious builders (non-coders very welcome)**  
If you’ve wanted to build an app with AI but didn’t know where to start, this project is a living playbook: small steps, clear acceptance criteria, reversible decisions, and a friendly assistant to explain the “why” along the way.

## The choices we made (and why they’re boring in a good way)

- **Static website with Hugo**: fast, accessible, and maintenance-light.  
- **Cloudflare Pages**: simple deploys, free SSL, and global edge caching.  
- **A tiny API** behind the scenes: enough to answer real questions (by name, by state, by map area, by distance) without over-engineering.  
- **SQLite for now**: one file, easy to ship and verify; we can scale later without changing the feel.  
- **Security & SEO basics**: sitemaps, canonical links, humane headers. Nothing flashy—just the stuff that keeps sites healthy.

## What the AI actually did here

No magic wand, just **calm instructions** when the UI played hide-and-seek and configuration got picky. We leaned on AI for:

- Step-by-step setup with copy/pasteable blocks.  
- “Explain the **why**” so decisions are teachable, not mysterious.  
- Guardrails like acceptance criteria and a runbook everyone can follow.  
- Quick debugging when we zigged into Workers instead of Pages (it happens 😅).

If you’re non-technical, this is the big takeaway: **you can do this**. Start small. Ask the assistant to talk you through each step. Ship something tiny. Repeat.

## The path so far

We stood up the public site, sketched a sane blog, added a little dev-only “is the API awake?” nudge, tightened DNS and SSL, and got the domain live. We also trimmed our records, set DMARC to monitor, and kept email intact. None of this is glamorous, but **it’s the foundation**.

Curious about the blow-by-blow?  
**Repo → Commits:** https://github.com/jspagnuolo/freshlocalharvest/commits/main

## What’s next

- Point the **Map** link to a hosted map UI backed by the API.  
- Add richer details (hours, seasonality, products, EBT specifics).  
- Invite the community to suggest corrections—and make it painless to review.  
- Keep the site friendly: quick loads, plain language, and just enough features to be helpful.

If this resonates—whether you’re hunting peaches, running a market, or thinking “maybe I could build something too”—you’re exactly who we’re building for. Welcome. 🌱
