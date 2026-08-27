# Existing-row preservation check

The baseline source is `edf2253^:data/results.csv`, immediately before the J-word export commit. The current file begins with those baseline bytes unchanged, then appends the new rows.

Command run from the repository:

```sh
uv run python - <<'PY'
import csv, hashlib, subprocess
baseline = subprocess.check_output(['git', 'show', 'edf2253^:data/results.csv'])
current = open('data/results.csv', 'rb').read()
assert current.startswith(baseline)
base_rows = list(csv.DictReader(baseline.decode().splitlines()))
current_rows = list(csv.DictReader(current.decode().splitlines()))
for name, rows in [('baseline', base_rows), ('current_prefix', current_rows[:len(base_rows)])]:
    random = [row for row in rows if row['method'] == 'random']
    encoded = '\\n'.join(','.join(row[field] for field in rows[0]) for row in random).encode() + b'\\n'
    print(name, len(rows), len(random), hashlib.sha256(encoded).hexdigest())
print('PREFIX_IDENTICAL', current[:len(baseline)] == baseline)
print('BASELINE_SHA256', hashlib.sha256(baseline).hexdigest())
print('CURRENT_PREFIX_SHA256', hashlib.sha256(current[:len(baseline)]).hexdigest())
print('ADDED_ROWS', len(current_rows) - len(base_rows))
PY
```

Observed output:

```text
baseline rows= 614 random_rows= 60 random_sha256= e2c6a95cc4e0362ad942566aae5d6f9edad46151980dfa276a38924ed31cf66a
current_prefix rows= 614 random_rows= 60 random_sha256= e2c6a95cc4e0362ad942566aae5d6f9edad46151980dfa276a38924ed31cf66a
PREFIX_IDENTICAL True
BASELINE_SHA256 9b1df05e6db5b7e522e10eb8d4548372ba754d6a26f6a27bdaf4ee001b1bada0
CURRENT_PREFIX_SHA256 9b1df05e6db5b7e522e10eb8d4548372ba754d6a26f6a27bdaf4ee001b1bada0
ADDED_ROWS 40
```

The equal prefix and random-row hash show that export appended ten J-word and thirty MLP-up arms without replacing baseline or random rows.
