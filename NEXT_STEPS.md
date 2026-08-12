# Next steps

The project is built, tested and committed locally. Here's what's left to make it live.

## 1. Create the GitHub repo and push

```bash
gh repo create rufic1337/taskflow-api --public --source=. --remote=origin
git push -u origin main
```

(Or create the repo manually on GitHub first, then `git remote add origin https://github.com/rufic1337/taskflow-api.git` and push.)

Once pushed, the CI workflow in `.github/workflows/ci.yml` will run automatically on every push/PR to `main` — it spins up Postgres and Redis services and runs the full test suite, including the WebSocket tests.

## 2. Deploy (Render, Docker runtime)

Create a new **Web Service** on Render pointing at the repo, with the Docker runtime (it will build the `Dockerfile` as-is — `daphne` serves both HTTP and WebSocket traffic on the same port, so no separate WebSocket service is needed).

Environment variables to set:

| Variable | Value | Notes |
|---|---|---|
| `SECRET_KEY` | a long random string | generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | `False` | |
| `ALLOWED_HOSTS` | `your-app.onrender.com` | comma-separated if you add a custom domain |
| `DATABASE_URL` | Render Postgres internal connection string | create a free Postgres instance first and copy its URL |
| `REDIS_URL` | *(optional)* | leave unset to use the in-memory channel layer and skip running a worker entirely — see below |
| `SEED_DEMO_DATA` | `true` | seeds the demo workspace/board/tasks on first boot; safe to leave `true`, the command is idempotent |
| `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` | notification emails just get logged; swap for a real backend (e.g. `django_ses`, SMTP) if you want them delivered |
| `CELERY_TASK_ALWAYS_EAGER` | `True` (if `REDIS_URL` is unset) | runs notification tasks synchronously, no worker process needed — good enough for a single free-tier instance |

**If you do want a real Celery worker + Redis broker** (closer to how this would run in production): add a Redis instance (Render's free Redis add-on, or Upstash), set `REDIS_URL`, set `CELERY_TASK_ALWAYS_EAGER=False`, and create a second Render service (Background Worker type) running `celery -A config worker -l info` against the same repo/image.

A second free Postgres instance may not be available on the same Render account as the e-commerce-api project — either share the existing Postgres server under a different database name, or use a separate free Postgres instance if your account allows more than one.

## 3. After deploying

- Update the **Live demo** line in `README.md` with the deployed URL (both `/api/docs/` for Swagger and the base API URL).
- Smoke-test the WebSocket in the browser console against the deployed host:
  ```js
  const token = "..."; // an access token from POST /api/auth/login/
  const ws = new WebSocket(`wss://your-app.onrender.com/ws/boards/1/?token=${token}`);
  ws.onmessage = (e) => console.log(JSON.parse(e.data));
  ```
- Log in as `demo@example.com` / `demopass123` (from the seed command) to explore the demo workspace and board.
