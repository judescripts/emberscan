# ADR 0001: Stack and hosting

**Status:** Accepted (2026-10-26)

## Context
Ten days, one builder, judged on impact, Meta AI tooling, demo and technical depth. Judges need a public URL that works live. The vision and video tooling (ffmpeg, OpenCV, SAM 3.1 parsers) is strongest in Python; the product is used on phones, so the UI must be mobile-first. The organizers list Streamlit apps and dashboard-first products as projects to avoid.

## Options
1. **Next.js (TypeScript) web + Python workers + Postgres + object storage.**
2. All-Python web app. Rejected: weaker mobile UI; drifts toward the Streamlit look.
3. All-TypeScript. Weaker for ffmpeg/OpenCV/geometry.

Hosting: **A.** Vercel (web) + Modal (workers) + Neon/Supabase Postgres. **B.** Azure Container Apps. **C.** Self-hosted tunnel (rejected: demo depends on one PC).

## Decision
- **Web:** Next.js (App Router, TypeScript) on **Vercel**. Mobile-first, light theme by default.
- **Workers:** Python on **Modal** for the pipeline (frames, SAM 3.1 calls, geometry, rules engine, agent). Modal also gives GPUs if we add monocular depth, and can serve the open-weight path (ADR 0006).
- **Data:** Postgres (Neon or Supabase) for properties, buildings, scans, hazards, rule results, fixes and agent traces. Object storage for uploads, frames and masks.
- **Queue:** a Postgres job table (`SELECT … FOR UPDATE SKIP LOCKED`), triggered by Modal functions; no extra broker.
- **Secrets:** environment variables only; `.env.example` committed, `.env` ignored; host secret stores in production.
- **Never** a Streamlit UI, even for internal tools.

## Consequences
- Two languages and two deployables, but each side uses its best tools. A clear service boundary (`POST /scans/{id}/process`) makes it easy to mock model outputs if access is slow.
- Free tiers cover the hackathon; Modal credits ($100) if approved.

## Re-check
- Modal credit approval; Neon vs Supabase decided when the DB is created (Day 2).
