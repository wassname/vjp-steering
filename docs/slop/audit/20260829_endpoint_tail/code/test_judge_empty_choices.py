"""Regression test: provider-empty responses must not consume format retries."""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
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

    responses = [SimpleNamespace(choices=[]), SimpleNamespace(choices=[]), SimpleNamespace(choices=[])]
    judge.request_with_rate_limit = request
    judge.asyncio.sleep = sleep
    try:
        await judge.judge_one(None, row, "AB", 0)
    except judge.DeferredCell:
        pass
    else:
        raise AssertionError("three empty responses did not defer the cell")
    finally:
        judge.request_with_rate_limit = original_request
        judge.asyncio.sleep = original_sleep

    class Client:
        async def close(self):
            return None

    async def deferred_judge(_client, _row, _order, _pass_index):
        raise judge.DeferredCell("empty choices after 3 attempts")

    original_client = judge.AsyncOpenAI
    original_judge_one = judge.judge_one
    original_deferred = judge.DEFERRED
    original_api_key = os.environ.get("OPENROUTER_API_KEY")
    with tempfile.TemporaryDirectory() as temporary_directory:
        judge.AsyncOpenAI = lambda **_kwargs: Client()
        judge.judge_one = deferred_judge
        judge.DEFERRED = Path(temporary_directory) / "deferred.jsonl"
        os.environ["OPENROUTER_API_KEY"] = "test"
        try:
            try:
                await judge.refresh([(row, "AB", 0)])
            except RuntimeError as error:
                assert str(error).startswith("JUDGE_DEFERRED cells=1")
            else:
                raise AssertionError("deferred cell did not fail refresh")
        finally:
            judge.AsyncOpenAI = original_client
            judge.judge_one = original_judge_one
            judge.DEFERRED = original_deferred
            if original_api_key is None:
                del os.environ["OPENROUTER_API_KEY"]
            else:
                os.environ["OPENROUTER_API_KEY"] = original_api_key
        record = json.loads((Path(temporary_directory) / "deferred.jsonl").read_text())
    assert record["cache_key"] and record["timestamp"] and record["reason"]

    original_client = judge.AsyncOpenAI
    original_judge_one = judge.judge_one
    original_deferred = judge.DEFERRED
    original_limit = judge.EMPTY_STORM_LIMIT
    original_api_key = os.environ.get("OPENROUTER_API_KEY")
    with tempfile.TemporaryDirectory() as temporary_directory:
        judge.AsyncOpenAI = lambda **_kwargs: Client()
        judge.judge_one = deferred_judge
        judge.DEFERRED = Path(temporary_directory) / "deferred.jsonl"
        judge.EMPTY_STORM_LIMIT = 1
        os.environ["OPENROUTER_API_KEY"] = "test"
        try:
            try:
                await judge.refresh([(row, "AB", 0)])
            except RuntimeError as error:
                assert str(error).startswith("JUDGE_PROVIDER_EMPTY_STORM cells=1")
            else:
                raise AssertionError("provider-empty storm did not stop refresh")
        finally:
            judge.AsyncOpenAI = original_client
            judge.judge_one = original_judge_one
            judge.DEFERRED = original_deferred
            judge.EMPTY_STORM_LIMIT = original_limit
            if original_api_key is None:
                del os.environ["OPENROUTER_API_KEY"]
            else:
                os.environ["OPENROUTER_API_KEY"] = original_api_key
        assert len((Path(temporary_directory) / "deferred.jsonl").read_text().splitlines()) == 1


asyncio.run(run())
print("JUDGE_EMPTY_CHOICES_SELF_TEST_PASS")
