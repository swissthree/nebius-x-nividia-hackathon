"""List the Nemotron models your Token Factory key can use, and send one "hello" call.

Usage:  python scripts/list_models.py
Needs NEBIUS_API_KEY in your environment or in .env.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import OpenAI  # noqa: E402

from app.config import get_settings  # noqa: E402

s = get_settings()
if not s.api_key:
    sys.exit("NEBIUS_API_KEY is not set — copy .env.example to .env and paste your key.")

client = OpenAI(base_url=s.base_url, api_key=s.api_key)
ids = sorted(m.id for m in client.models.list().data)
nemotron = [i for i in ids if "nemotron" in i.lower()]
print(f"{len(ids)} models available; Nemotron models:")
for i in nemotron:
    print("  ", i)

print("\nConfigured tiers:")
for tier, model in [("nano", s.nano_model), ("super", s.super_model), ("ultra", s.ultra_model)]:
    if model in ids:
        flag = "OK"
    else:
        near = next((i for i in ids if i.lower() == model.lower()), None)
        flag = f"NOT FOUND — did you mean {near}? (IDs are case-sensitive)" if near else "NOT FOUND — update .env"
    print(f"  {tier:<6} {model}  [{flag}]")

if s.nano_model in ids:
    r = client.chat.completions.create(
        model=s.nano_model, max_tokens=40,
        messages=[{"role": "user", "content": "Say hello from Nemotron in one short sentence."}],
    )
    print("\nHello call:", (r.choices[0].message.content or "").strip())
