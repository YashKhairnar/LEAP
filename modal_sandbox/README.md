# LEAP Modal sandbox

This service runs learner Python code in a single-use Modal container. The
container includes the runtime datasets and common ML packages, so Render does
not upload a dataset on every execution.

## Deploy

From the repository root:

```bash
python3 -m pip install -r modal_sandbox/requirements.txt
modal setup
modal secret create leap-sandbox-secrets MODAL_SANDBOX_TOKEN="$(openssl rand -hex 32)"
modal deploy modal_sandbox/app.py
```

Copy the deployed endpoint into Render as `MODAL_SANDBOX_URL`. Set the same
token value as `MODAL_SANDBOX_TOKEN` in Render. Set
`MODAL_SANDBOX_SECRET_NAME` only if you use a different Modal secret name.

The function uses a single-use container, disables outbound network access,
limits CPU/memory/time, and restricts Modal control-plane access. Do not expose
the endpoint without its shared token.
