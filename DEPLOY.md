# Deploying the demo to Nebius

Goal: a public URL judges can open with no login, running on a **Nebius Serverless Endpoint** and calling **Nebius Token Factory**.

**Route used (no Docker needed on your PC):** GitHub Actions builds the image on every push to `main` and publishes it to GitHub Container Registry (GHCR). The Nebius endpoint pulls it from there.

```
git push ──► GitHub Actions: tests → docker build → health check → push ghcr.io/swissthree/nebius-x-nividia-hackathon:latest
                                                                          │
Nebius Serverless Endpoint (eu-west2) ◄──────── pulls image ─────────────┘  ──► calls Token Factory (Nemotron)
```

> Docs: [Serverless endpoints quickstart](https://docs.nebius.com/serverless/quickstart/endpoints) · [Manage endpoints](https://docs.nebius.com/serverless/endpoints/manage). Flags can change: if a command errors, run `nebius ai endpoint create --help`.

## 1. Publish the image (one-time setup)
1. Push to `main`. Watch the **Actions** tab on GitHub; both jobs (`test`, `image`) should go green.
2. Make the image public so Nebius can pull it without a password: GitHub → your profile → **Packages** → `nebius-x-nividia-hackathon` → **Package settings** → **Change visibility** → **Public**.

After that, every push to `main` publishes a fresh `:latest`.

## 2. Create the endpoint (in WSL / Ubuntu)
Open a terminal, run `wsl`, then:

```bash
cd "/mnt/c/Users/marcu/OneDrive/Desktop/github/projects/nebius-x-nividia-hackathon"

# Load the API key from .env without typing it (strips Windows line endings)
export NEBIUS_API_KEY=$(grep '^NEBIUS_API_KEY=' .env | cut -d= -f2- | tr -d '\r')
echo "key loaded: ${#NEBIUS_API_KEY} characters"     # should be > 100; never prints the key

nebius ai endpoint create \
  --name meeting-to-actions \
  --image ghcr.io/swissthree/nebius-x-nividia-hackathon:latest \
  --container-port 8000 \
  --platform cpu-d3 \
  --preset 4vcpu-16gb \
  --public \
  --env "NEBIUS_API_KEY=$NEBIUS_API_KEY,LLM_CACHE=1,RATE_LIMIT_PER_MINUTE=5,DAILY_RUN_CAP=300"
```

- **No `--auth` flag** = the URL is open to anyone (what judges need). The app's rate limit and daily cap protect your credits.
- The CLI will **prompt for a subnet**: pick the default one.
- **Preset:** choose the smallest CPU preset offered. The app is tiny; the heavy work happens in Token Factory. A running endpoint bills continuously, so check your AI Cloud credits.

## 3. Get the URL and test
```bash
export ENDPOINT_ID=$(nebius ai endpoint get-by-name --name meeting-to-actions --format jsonpath='{.metadata.id}')
nebius ai endpoint get "$ENDPOINT_ID" --format json | grep -o 'https://[^"]*' | head -1
```
Open the URL in a private window. The badge should say **LIVE · Token Factory**. Run each sample (instant, from the recorded replies), then one custom transcript (live).

Logs if something's wrong: `nebius ai endpoint logs $ENDPOINT_ID`

## Updating the demo later
Push to `main` → wait for the green Actions run → recreate the endpoint so it pulls the new `:latest`:
```bash
nebius ai endpoint delete $ENDPOINT_ID   # then run step 2 again
```
If you change prompts or models, re-record the sample replies first: `py scripts/smoke_test.py`, then copy the new files from `.cache/llm/` into `demo_cache/` (the `test_demo_cache` test tells you when they're stale).

## After judging
The endpoint bills while it runs: `nebius ai endpoint delete $ENDPOINT_ID`

## Alternative: build on your PC
Install Docker Desktop, then build and push to Nebius Container Registry instead of GHCR:
```bash
export REGION_ID=eu-west2
export REGISTRY_PATH=$(nebius registry create --name m2a-registry --format json | jq -r ".metadata.id" | cut -d- -f 2)
nebius registry configure-helper
export IMAGE=cr.$REGION_ID.nebius.cloud/$REGISTRY_PATH/meeting-to-actions:v1
docker build --platform linux/amd64 -t $IMAGE . && docker push $IMAGE
```
Then use `--image $IMAGE` in step 2.
