# Production Deployment

This repo is prepared for a split deployment:

- Frontend: Vercel, using `app/templates/initial frontend`
- Backend API: Hugging Face Spaces, using the root `Dockerfile`

## Backend on Hugging Face Spaces

Create a new Hugging Face Space with Docker as the SDK, then push the repo root.

Set these Space secrets or variables:

```env
APP_ENV=production
PORT=7860
WEB_CONCURRENCY=1
JWT_SECRET_KEY=<long-random-secret>
SECRET_KEY=<long-random-secret>
FRONTEND_URL=https://your-vercel-project.vercel.app
ALLOWED_ORIGINS=https://your-vercel-project.vercel.app
COOKIE_SECURE=true
DATABASE_URL=sqlite:////data/hispro.db
```

Enable persistent storage for the Space if you use the default SQLite database.
Without persistent storage, the database can be reset when the Space rebuilds.

For a stronger production database, use managed PostgreSQL and set:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME
```

After deploy, verify:

```text
https://your-huggingface-space.hf.space/health
https://your-huggingface-space.hf.space/docs
```

## Frontend on Vercel

Import the repo into Vercel and set the project root directory to:

```text
app/templates/initial frontend
```

Set this Vercel environment variable:

```env
VITE_API_BASE_URL=https://your-huggingface-space.hf.space/api/v1
TENANT_BASE_DOMAIN=his.pro
PUBLIC_APP_ORIGIN=https://your-vercel-project.vercel.app
```

`TENANT_BASE_DOMAIN` must match a wildcard domain already assigned to the Vercel
project with working DNS and TLS, for example `*.his.pro`. Do not set it to the
generated project hostname: owning `his-pro.vercel.app` does not provide
`*.his-pro.vercel.app` wildcard routing.

The frontend and backend are cross-origin in production. Keep the backend URL
HTTPS, keep `COOKIE_SECURE=true`, and set `ALLOWED_ORIGINS` to the exact Vercel
domain so HttpOnly auth cookies work with CORS credentials.

The included `vercel.json` handles Vite SPA rewrites so routes like
`/login/my-facility` and `/dashboard/my-facility` load correctly on refresh.

## Production Checks

Run these before pushing:

```bash
cd app/templates/initial\ frontend
npm test -- --run
npm run build
cd ../../..
.venv/Scripts/python.exe tests/test_setup_endpoints.py
```

On Windows PowerShell, use:

```powershell
Set-Location "app/templates/initial frontend"
npm test -- --run
npm run build
Set-Location ../../..
.\.venv\Scripts\python.exe tests\test_setup_endpoints.py
```
