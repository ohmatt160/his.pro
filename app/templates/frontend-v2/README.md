# HIS Pro Frontend v2.0

This directory is an independent visual and interaction revision of the HIS Pro frontend.
The existing `app/templates/initial frontend` application remains unchanged.

## Run

```powershell
npm install
npm run dev
```

V2 runs on `http://127.0.0.1:5174` by default.

## Architecture

- Existing API and route contracts remain compatible.
- Pages are lazy-loaded and server data uses bounded React Query caching.
- WebSocket events update tenant-scoped caches without polling every page visit.
- Navigation and quick actions are derived from the signed-in role and enabled modules.

## Security boundaries

- Access tokens remain in memory; refresh and CSRF use server-issued cookies.
- Facility, branch, role, and module guards wrap protected routes.
- Cross-origin API URLs are rejected before credentials can be attached.
- Realtime events are checked against the current facility, user, role, and branch.
- The backend remains the final authorization and tenant-isolation authority.

## Vercel staging connection

Create a separate Vercel project for this branch and set its Root Directory to
`app/templates/frontend-v2`. Configure these project environment variables:

- `VITE_API_BASE_URL=/api/v1`
- `HF_BACKEND_URL=<HTTPS origin of the HIS.Pro staging Space>`
- `HF_TOKEN=<server-side Hugging Face access token>` when the Space is private
- `VITE_REALTIME_WS_URL=<direct WSS base>` only when staging exposes a direct
  WebSocket endpoint and that endpoint allows this Vercel origin

The Vercel API proxy forwards HTTP requests to `HF_BACKEND_URL`, keeping the
backend host and optional token server-side. Do not add `HF_TOKEN` with a `VITE_`
prefix. Do not point `VITE_REALTIME_WS_URL` at the Vercel HTTP proxy; WebSockets
are disabled by default and become active only with an explicit direct endpoint.
Set `PUBLIC_APP_ORIGIN` and the staging backend's allowed frontend origin to the
Vercel deployment origin so email links and browser-origin checks are correct.

Use the branch's preview deployment for pilot testing. Production secrets and
production backend URLs belong only in the production project's settings.
