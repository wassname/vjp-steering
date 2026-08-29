"""Regression test: provider-empty responses must not consume format retries."""

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import endpoint_tail_manifest
import judge


async def run() -> None:
    row = endpoint_tail_manifest.judge_rows(ROOT / "outputs/endpoint_tail_manifest.json")[0]
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps({
                "evidence": "The response contains a valid score record.",
                "on_axis_A": 1,
                "on_axis_B": 0,
                "off_axis_A": 1,
                "off_axis_B": 1,
            }),
            reasoning=None,
        ))],
        usage=SimpleNamespace(cost=0),
        provider="test",
    )
    responses = [SimpleNamespace(choices=[]), SimpleNamespace(choices=[]), response]

    async def request(_client, _content):
        return responses.pop(0)

    async def sleep(_seconds):
        return None

    original_request = judge.request_with_rate_limit
    original_sleep = judge.asyncio.sleep
    judge.request_with_rate_limit = request
    judge.asyncio.sleep = sleep
    try:
        record = await judge.judge_one(None, row, "AB", 0)
    finally:
        judge.request_with_rate_limit = original_request
        judge.asyncio.sleep = original_sleep
    assert not responses
    assert len(record["raw_attempts"]) == 1


asyncio.run(run())
print("JUDGE_EMPTY_CHOICES_SELF_TEST_PASS")
