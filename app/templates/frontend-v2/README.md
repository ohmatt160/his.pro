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
