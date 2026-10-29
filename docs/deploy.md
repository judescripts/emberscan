# Deploying EmberScan

Vercel (web) + Modal (worker) + Neon (Postgres), per [ADR 0001](adr/0001-stack-and-hosting.md).

```
phone ──4 MB slices──▶ Vercel  /api/uploads ──▶ Modal  PUT /uploads/{id}/{clip}   (appends on the Volume)
      ──start scan───▶ Vercel  /api/scans   ──▶ Modal  POST /uploads/{id}/scan   (scan runs in the container)
                       Vercel ◀── Neon (communities, buildings, scans)
```

Vercel functions accept at most 4.5 MB per request and don't share a disk, so the browser sends
each clip in 4 MB slices and the web app passes every slice straight on to the worker. The worker
token stays on the server; the browser never talks to Modal.

## Worker (Modal)

From `workers/`, once `modal token new` has been run:

```bash
modal secret create emberscan-worker --force META_API_KEY=… BASETEN_API_KEY=… WORKER_TOKEN=… …
modal deploy modal_app.py
```

- The secret holds the keys from `.env` (see `.env.example`) plus `WORKER_TOKEN`. Keep the token
  in a gitignored `.env.deploy`; the same value goes to Vercel.
- Scans, uploads and the spend ledger live on the Volume `emberscan-data` (`/data/scans`).
- One container (`max_containers=1`): scans run as background tasks inside it and the daily
  budget is counted from its files. It stays up 20 minutes after the last request.
- `modal shell` doesn't work on Windows; use `modal app logs emberscan-worker` for output.

## Database (Neon)

Installed through the Vercel marketplace, which sets `DATABASE_URL` on the project:

```bash
vercel integration add neon --name emberscan-db --no-env-pull -e production -e preview
```

`--no-env-pull` matters: a `DATABASE_URL` in `apps/web/.env.local` would point local dev at the
production database. To migrate, pass the URL for that one command only:

```bash
DATABASE_URL=… npm run db:migrate      # from apps/web
```

## Web (Vercel)

From `apps/web/` (project `emberscan`, linked with `vercel link`):

```bash
vercel env add WORKER_URL production      # https://<workspace>--emberscan-worker-web.us-east.modal.run
vercel env add WORKER_TOKEN production
vercel env add SCAN_PASSCODE production   # gates the paid step; browsing stays open
vercel deploy --prod
```

The project isn't connected to GitHub, so pushes don't deploy; run `vercel deploy --prod`.
