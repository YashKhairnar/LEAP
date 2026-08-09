# LEAP deployment

LEAP is designed for a Vercel frontend, Render FastAPI service, and Neon PostgreSQL database.

## 1. Push the repository

Create a GitHub repository and push this directory. Do not commit `.env` files, database files, or credentials.

## 2. Create Neon PostgreSQL

Create a Neon project and copy its pooled PostgreSQL connection string. It must include TLS settings such as `sslmode=require`. Keep this value secret.

## 3. Deploy the backend on Render

Create a Render Blueprint from the repository. `render.yaml` configures the `backend` directory.

Set these secret environment variables:

- `DATABASE_URL`: the Neon pooled connection string
- `FRONTEND_ORIGINS`: the exact Vercel production origin, for example `https://leap.example.vercel.app`

The service health check is `/health`. Schema creation runs when the API starts.

## 4. Deploy the frontend on Vercel

Import the same repository and select `frontend` as the Root Directory.

Set:

- `BACKEND_URL`: the Render service origin, currently `https://leap-api-tdy5.onrender.com`

Do not set `NEXT_PUBLIC_API_URL` in production. The included Next.js rewrite proxies `/api/*`
through the Vercel origin, allowing the secure authentication cookie to remain first-party.
Redeploy after changing `BACKEND_URL`.

## 5. Production verification

1. Open the Vercel `/signup` page.
2. Accept the research notice and create a test account.
3. Complete one incorrect and one correct question attempt.
4. Confirm Neon contains one user, content rows, and ordered transition/event rows.
5. Restart the Render service and confirm login and data still work.
6. Delete the test account/data before inviting participants.

## Research launch gate

The included notice is explicitly a draft. Replace it with institution-approved wording and obtain any required IRB/ethics approval before formal human-subjects data collection. Training exports must exclude the `users` and `auth_sessions` tables and use only generated `learner_id` values.
