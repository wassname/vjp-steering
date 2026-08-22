"""Reproduce one judge cell to inspect the raw invalid response. One-off diagnostic."""

import asyncio
import json
import sys

sys.path.insert(0, "scripts")
import judge
from openai import AsyncOpenAI
import os


async def main() -> None:
    rows = judge.manifest([], walks=True)
    cells = judge.required_cells(rows)
    row, order, pass_index = cells["d1f63507328ae816d47e2e871e1013e47305d112ad43a93684fad7eb65697e9d"]
    client = AsyncOpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
        max_retries=2,
    )
    prompt = judge.judge_prompt(row, order)
    print("PROMPT_TAIL_CHARS", len(prompt))
    variants = [
        ({"role": "user", "content": prompt}, 0.7),
        ({"role": "user", "content": prompt + "\n\nOutput only the JSON object now. Do not repeat any text from the responses."}, 0.7),
        ({"role": "user", "content": prompt + "\n\nOutput only the JSON object now. Do not repeat any text from the responses."}, 1.3),
    ]
    for attempt, (messages, temp) in enumerate(variants):
        try:
            response = await client.chat.completions.create(
                model=judge.MODEL,
                messages=[messages],
                temperature=temp,
                max_tokens=1024,
                response_format=judge.FORMAT,
                extra_body={
                    "min_p": 0.1,
                    "reasoning": {"enabled": False},
                    "provider": {
                        "quantizations": ["fp8", "int8", "bf16", "fp16"],
                        "require_parameters": True,
                        "ignore": ["AtlasCloud", "DeepInfra"],
                    },
                },
            )
        except Exception as exc:
            print(f"--- attempt {attempt} temp={temp} EXC: {exc}")
            continue
        print("routed provider:", getattr(response, "provider", "unknown"))
        raw = response.choices[0].message.content
        ok = False
        try:
            ok = judge.valid(json.loads(raw))
        except Exception:
            pass
        print(f"--- attempt {attempt} temp={temp} finish={response.choices[0].finish_reason} len={len(raw or '')} VALID={ok}")
        print(repr(raw)[:400])
    await client.close()


asyncio.run(main())
