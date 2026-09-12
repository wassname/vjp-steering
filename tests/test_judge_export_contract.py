"""Offline caller regressions for judge/export contracts. Author: PI/gpt-6-astra."""

import asyncio
import csv
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import export
import judge


def write_jsonl(path, records):
    path.write_text("".join(json.dumps(record) + "\n" for record in records))


def rating(order):
    return {
        "evidence": "Fixture: steered response has greater target disposition.",
        "on_axis_A": 0.2 if order == "AB" else 1.2,
        "on_axis_B": 1.2 if order == "AB" else 0.2,
        "off_axis_A": 0.1 if order == "AB" else 0.3,
        "off_axis_B": 0.3 if order == "AB" else 0.1,
    }


def cache_entries(rows, passes, rubric):
    return [
        {
            "cache_key": key, "model": judge.MODEL, "rubric_version": rubric,
            "order": order, "pass": pass_index, "vignette": row["vignette"],
            "side": row["side"], "judgment": rating(order),
        }
        for key, (row, order, pass_index) in judge.required_cells(rows, passes=passes, rubric=rubric).items()
    ]


class Http500(Exception):
    status_code = 500
    body = {}


class TestJudgeCaller(unittest.TestCase):
    def setUp(self):
        scenario, item = next(iter(judge.load_cohort().items()))
        self.row = {
            "prompt": item["prompt"], "vignette": scenario, "side": "+C",
            "bare": "A bare response.", "steered": "A steered response.",
            "run": "fixture", "method": "mean_diff", "source": "fixture.jsonl",
        }

    def test_http_exhaustion_counts_actual_client_requests(self):
        create = AsyncMock(side_effect=Http500())
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        with patch.object(judge.asyncio, "sleep", AsyncMock()) as sleep:
            with self.assertRaisesRegex(RuntimeError, "transient 500 after 3 attempts"):
                asyncio.run(judge.judge_one(client, self.row, "AB", 0))
        self.assertEqual(create.await_count, 3)
        self.assertEqual([call.args[0] for call in sleep.await_args_list], [1.5, 3.0])

    def test_transient_budget_is_separate_from_format_budget(self):
        bad_json = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="bad JSON"))])
        create = AsyncMock(side_effect=[Http500(), bad_json, Http500(), Http500()])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        with patch.object(judge.asyncio, "sleep", AsyncMock()):
            with self.assertRaisesRegex(RuntimeError, "transient 500 after 3 attempts"):
                asyncio.run(judge.judge_one(client, self.row, "AB", 0))
        self.assertEqual(create.await_count, 4)

    def test_legacy_prompt_hashes_are_unchanged(self):
        hashes = {
            ("+C", "AB"): "3b8d6b247883e7383bbaa5bdc3ced9303e30c7e7a2b4d1f6d8d63ca9db4d54f7",
            ("+C", "BA"): "d91e1fab407e9f8f6ed4c486027243ffed8b9abb3bf428f6e41320488f178a76",
            ("-C", "AB"): "73e94cf57a23a0c311f45204ca02bb7fd1d10d280994b5a4cf5379b0a7b6d6f9",
            ("-C", "BA"): "73d4bbba18c684732f681e44ba4fcfb55c980da8319c3a7d83eca9d3c44f1cf4",
        }
        with patch.object(judge, "answer_key", return_value="The premise is false."):
            for (side, order), expected in hashes.items():
                row = {**self.row, "side": side, "prompt": "Why is this flawed?"}
                self.assertEqual(judge.sha(judge.judge_prompt(row, order, rubric=judge.LEGACY_RUBRIC)), expected)

    def test_client_prompt_and_saved_record_share_explicit_rubric(self):
        for side, target, sign in (("+C", None, "negative"), ("-C", None, "positive"), ("+C", "candidness", "positive")):
            for rubric in judge.RUBRICS:
                with self.subTest(side=side, target=target, rubric=rubric):
                    row = {**self.row, "side": side, "behavior_target": target}
                    response = SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(rating("AB"))))],
                        usage=SimpleNamespace(cost=0),
                    )
                    create = AsyncMock(return_value=response)
                    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
                    record = asyncio.run(judge.judge_one(client, row, "AB", 0, rubric=rubric))
                    prompt = create.await_args.kwargs["messages"][0]["content"]
                    self.assertEqual(record["prompt"], prompt)
                    self.assertEqual(record["rubric_version"], rubric)
                    self.assertEqual(record["cache_key"], judge.cache_key(row, "AB", 0, rubric=rubric))
                    if rubric == judge.RUBRIC:
                        self.assertIn(f"candidness contributes {sign} on-axis evidence", prompt)
                        self.assertNotIn("Naming the flaw is the target behaviour", prompt)
                        self.assertNotIn("score that as target behaviour", prompt)
                    else:
                        self.assertIn("Naming the flaw is the target behaviour", prompt)
                    self.assertEqual(create.await_count, 1)

    def test_cache_versions_never_collide_or_fallback(self):
        old = judge.required_cells([self.row], rubric=judge.LEGACY_RUBRIC)
        new = judge.required_cells([self.row], rubric=judge.RUBRIC)
        self.assertTrue(set(old).isdisjoint(new))
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "cache.jsonl"
            entries = cache_entries([self.row], 2, judge.LEGACY_RUBRIC)
            write_jsonl(cache, entries)
            with patch.object(export, "CACHE", cache), patch.object(judge, "CACHE", cache):
                self.assertEqual(set(export.cache_records(set(old), rubric=judge.LEGACY_RUBRIC)), set(old))
                self.assertEqual(judge.cached_keys(rubric=judge.LEGACY_RUBRIC), set(old))
                self.assertEqual(judge.cached_keys(), set())
                with self.assertRaisesRegex(ValueError, "required cells missing"):
                    export.cache_records(set(new))
                entries[0]["cache_key"] = next(iter(new))
                write_jsonl(cache, entries)
                with self.assertRaisesRegex(ValueError, "required cells missing"):
                    export.cache_records({entries[0]["cache_key"]})


class TestExportCaller(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = self.root / "judgments.jsonl"
        self.results = self.root / "results.csv"
        self.scenarios = self.root / "judged_scenarios.csv"
        for path, fields in ((self.results, export.FIELDS), (self.scenarios, export.SCENARIO_FIELDS)):
            path.write_text(",".join(fields) + "\n")
        for module, name, value in (
            (export, "CACHE", self.cache), (export, "RESULTS", self.results),
            (export, "SCENARIOS", self.scenarios),
        ):
            self.enterContext(patch.object(module, name, value))
        self.cohort = judge.load_cohort()
        self.run = self.root / "run_20260912_fixture"
        self.run.mkdir()
        self.artifact = self.run / "mean_diff.json"
        self.artifact.write_text(json.dumps({
            "status": "RESULT", "persona": "sycophancy_abrasive", "axis": "sycophancy",
            "demo_set": "sycophancy_all100", "eval_version": 10,
            "method": "mean_diff", "seed": 0, "model": "fixture-model", "layers": [1],
            "batch_size": 4, "fixed_coefficient_magnitude": 1.0,
            "breakdown_reasons": {"+C": [], "-C": []},
        }))
        self.generations = [
            {"scenario": scenario, "prompt": item["prompt"], "steer_direction": side,
             "text": f"{scenario} {side or 'bare'} response"}
            for scenario, item in self.cohort.items() for side in (None, "+C", "-C")
        ]
        write_jsonl(self.run / "moral_demos.jsonl", self.generations)
        self.enterContext(patch.object(export, "artifact_paths", return_value=[self.artifact]))
        self.entries = cache_entries(judge.demo_rows(self.artifact), 2, judge.LEGACY_RUBRIC)
        write_jsonl(self.cache, self.entries)

    def snapshot(self):
        return {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}

    def test_legacy_cli_writes_complete_scenarios_and_both_signed_effects(self):
        with patch.object(sys, "argv", ["export.py", "--run", self.run.name, "--rubric", judge.LEGACY_RUBRIC]):
            export.main()
        with self.results.open() as file:
            rows = list(csv.DictReader(file))
        with self.scenarios.open() as file:
            scenarios = list(csv.DictReader(file))
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(scenarios), 200)
        for row in rows:
            self.assertAlmostEqual(float(row["effect"]), 1 if row["side"] == "+C" else -1)
            self.assertAlmostEqual(float(row["off_axis_perturbation"]), 0.2)
            self.assertEqual(row["admissible"], "True")
            self.assertEqual({r["scenario"] for r in scenarios if r["side"] == row["side"]}, set(self.cohort))
        self.assertEqual({r["order_reversal"] for r in scenarios}, {"False"})
        self.assertEqual({float(r["score_spread"]) for r in scenarios}, {0.0})

    def test_missing_order_pass_or_whole_scenario_stops_before_any_write(self):
        first = next(iter(self.cohort))
        removals = {
            "one_order": lambda r: r["order"] == "BA",
            "paired_pass": lambda r: r["pass"] == 1,
            "whole_scenario": lambda r: r["vignette"] == first,
        }
        for name, remove in removals.items():
            with self.subTest(missing=name):
                write_jsonl(self.cache, [r for r in self.entries if not remove(r)])
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, "required cells missing"):
                    export.export([self.run.name], rubric=judge.LEGACY_RUBRIC)
                self.assertEqual(self.snapshot(), before)

    def test_missing_generated_scenario_stops_before_any_write(self):
        write_jsonl(self.run / "moral_demos.jsonl", self.generations[3:])
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "incomplete all100 generations"):
            export.export([self.run.name], rubric=judge.LEGACY_RUBRIC)
        self.assertEqual(self.snapshot(), before)

    def test_v8_cannot_append_to_historical_aggregate(self):
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "v8 needs a new full-cohort result schema"):
            export.export([self.run.name])
        self.assertEqual(self.snapshot(), before)

    def experiment_fixture(self, rubric=judge.RUBRIC):
        root = self.root / "experiment"
        root.mkdir()
        output = self.root / "experiment_export"
        bare = [{"scenario": s, "prompt": item["prompt"], "text": f"{s} bare"} for s, item in self.cohort.items()]
        write_jsonl(root / "bare.jsonl", bare)
        manifest = {
            "method": "mean_diff", "config": {"seed": 0, "batch_size": 4},
            "bare": {"path": "bare.jsonl"}, "cohort_sha256": "fixture-cohort", "date": "20260912",
            "extraction": {"model": "fixture-model", "source_layers": [1]}, "cells": {},
        }
        for side in ("+C", "-C"):
            filename = f"{side}.jsonl"
            write_jsonl(root / filename, [{**r, "text": f"{r['scenario']} {side}"} for r in bare])
            manifest["cells"][side] = {"1": {"coefficient": 1.0, "rows": 100, "path": filename, "breakdown_reasons": []}}
        (root / "manifest.json").write_text(json.dumps(manifest))
        self.enterContext(patch.object(judge, "experiment_dir", return_value=root))
        self.enterContext(patch.object(export, "experiment_dir", return_value=root))
        self.enterContext(patch.object(export, "data_dir", return_value=output))
        entries = cache_entries(judge.experiment_rows("fixture", "full", all_generated=True), 1, rubric)
        write_jsonl(self.cache, entries)
        return root, output, entries

    def test_experiment_writes_current_contract_and_complete_cohort(self):
        _, output, _ = self.experiment_fixture()
        export.export_experiment("fixture", "full", all_generated=True)
        contract = json.loads((output / "judge_contract.json").read_text())
        self.assertEqual(contract, {"rubric": judge.RUBRIC, "model": judge.MODEL, "orders": ["AB", "BA"], "passes": 1})
        with (output / "judged_scenarios.csv").open() as file:
            scenarios = list(csv.DictReader(file))
        self.assertEqual(len(scenarios), 200)
        selected = json.loads((output / "selected.json").read_text())
        self.assertEqual({side: value["effect"] for side, value in selected["sides"].items()}, {"+C": 1.0, "-C": -1.0})

    def test_experiment_missing_judgments_cannot_create_output(self):
        _, output, entries = self.experiment_fixture()
        write_jsonl(self.cache, entries[1:])
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "required cells missing"):
            export.export_experiment("fixture", "full", all_generated=True)
        self.assertFalse(output.exists())
        self.assertEqual(self.snapshot(), before)

    def test_experiment_duplicate_scenario_cannot_publish_all100(self):
        root, output, _ = self.experiment_fixture()
        records = [json.loads(line) for line in (root / "+C.jsonl").read_text().splitlines()]
        records[-1] = records[0]
        write_jsonl(root / "+C.jsonl", records)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "incomplete or duplicate full scenarios"):
            export.export_experiment("fixture", "full", all_generated=True)
        self.assertFalse(output.exists())
        self.assertEqual(self.snapshot(), before)

    def test_experiment_contract_mismatch_or_unversioned_history_stops_before_writes(self):
        _, output, _ = self.experiment_fixture()
        output.mkdir()
        (output / "results.csv").write_text("historical fixture\n")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "existing export lacks judge contract"):
            export.export_experiment("fixture", "full", all_generated=True)
        self.assertEqual(self.snapshot(), before)
        (output / "judge_contract.json").write_text(json.dumps({"rubric": judge.LEGACY_RUBRIC}))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "judge contract mismatch"):
            export.export_experiment("fixture", "full", all_generated=True)
        self.assertEqual(self.snapshot(), before)

    def test_explicit_v7_can_reexport_unversioned_history_without_relabeling(self):
        _, output, _ = self.experiment_fixture(judge.LEGACY_RUBRIC)
        output.mkdir()
        (output / "results.csv").write_text("historical fixture\n")
        export.export_experiment("fixture", "full", all_generated=True, rubric=judge.LEGACY_RUBRIC)
        self.assertEqual(json.loads((output / "judge_contract.json").read_text())["rubric"], judge.LEGACY_RUBRIC)


if __name__ == "__main__":
    unittest.main()
