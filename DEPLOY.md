# Deploying the demo to Nebius

Goal: a public URL judges can open with no login, running on **Nebius AI Cloud** (Serverless Endpoint) and calling **Nebius Token Factory**.

> Commands below come from the Nebius docs (Oct 2026). Flags can change — if a command errors, run it without flags and the CLI prompts for each value.
> Docs: [Serverless endpoints quickstart](https://docs.nebius.com/serverless/quickstart/endpoints) · [Manage endpoints](https://docs.nebius.com/serverless/endpoints/manage) · [Container Registry quickstart](https://docs.nebius.com/container-registry/quickstart)

## 0. Prerequisites
- Docker, the `nebius` CLI (logged in, project selected), `jq`
- Your Token Factory key working locally (`python scripts/list_models.py` succeeds)

## 1. Record the demo replies (recommended)
Bakes real Nemotron answers for the three samples into the image, so the sample demo is instant, identical every time and free on judging day. Custom transcripts still go live to Token Factory.

```bash
python scripts/smoke_test.py          # runs samples live, caches replies in .cache/llm/
cp .cache/llm/*.json demo_cache/
```

## 2. Build and push the image
```bash
export REGION_ID=eu-north1            # or your region: us-central1, eu-west1, ...
export REGISTRY_PATH=$(nebius registry create --name m2a-registry --format json | jq -r ".metadata.id" | cut -d- -f 2)
nebius registry configure-helper      # sets up docker auth (don't run docker as root)

export IMAGE=cr.$REGION_ID.nebius.cloud/$REGISTRY_PATH/meeting-to-actions:v1
docker build --platform linux/amd64 -t $IMAGE .
docker push $IMAGE
```

Quick local check before pushing:
```bash
docker run --rm -p 8000:8000 --env-file .env -e LLM_CACHE=1 $IMAGE
# open http://localhost:8000
```

## 3. Create the endpoint
Leaving out `--auth` makes the endpoint public (no token needed) — that's what judges need. The rate limiter in the app protects your credits.

```bash
nebius ai endpoint create \
  --name meeting-to-actions \
  --image $IMAGE \
  --platform cpu-d3 \
  --preset 4vcpu-16gb \
  --container-port 8000 \
  --public \
  --env "LLM_CACHE=1,RATE_LIMIT_PER_MINUTE=5,DAILY_RUN_CAP=300" \
  --env-secret NEBIUS_API_KEY=<secret_selector>
```

- **API key:** store it in SecretStash and pass it with `--env-secret` (keeps it out of shell history). If that's a hassle, `--env "NEBIUS_API_KEY=..."` also works.
- **Model IDs:** if `list_models.py` showed different IDs than the defaults, add them to `--env` too (`NEMOTRON_NANO_MODEL=...` etc.).
- **Preset:** pick the smallest CPU preset your project offers — the app is tiny; all heavy lifting happens in Token Factory.
- `--subnet-id` is required; the CLI prompts for it if omitted.

## 4. Get the URL and test
```bash
export ENDPOINT_ID=$(nebius ai endpoint get-by-name --name meeting-to-actions --format jsonpath='{.metadata.id}')
nebius ai endpoint get "$ENDPOINT_ID" --format json | jq -r '.status.public_endpoints[] | select(startswith("https://"))'
```
Open the URL logged out / in a private window. The badge in the top right should say **LIVE · Token Factory**. Run each sample, then one custom transcript.

Logs: `nebius ai endpoint logs $ENDPOINT_ID`

## 5. After judging
The endpoint bills while it runs. Delete it once judging is over: `nebius ai endpoint delete $ENDPOINT_ID`

## Fallback
If the Serverless Endpoint gives trouble close to the deadline, the same image runs on any container host. The project still satisfies "runs on Token Factory" because all model calls go there — but Nebius hosting is encouraged, so try it first.
