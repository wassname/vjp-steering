# Existing-row preservation check

The baseline source is `edf2253^:data/results.csv`, immediately before the J-word export commit. The current file begins with those baseline bytes unchanged, then appends the new rows.

```text
baseline rows= 614 random_rows= 60 random_sha256= e2c6a95cc4e0362ad942566aae5d6f9edad46151980dfa276a38924ed31cf66a
current_prefix rows= 614 random_rows= 60 random_sha256= e2c6a95cc4e0362ad942566aae5d6f9edad46151980dfa276a38924ed31cf66a
PREFIX_IDENTICAL True
BASELINE_SHA256 9b1df05e6db5b7e522e10eb8d4548372ba754d6a26f6a27bdaf4ee001b1bada0
CURRENT_PREFIX_SHA256 9b1df05e6db5b7e522e10eb8d4548372ba754d6a26f6a27bdaf4ee001b1bada0
ADDED_ROWS 40
```

The equal prefix and random-row hash show that export appended ten J-word and thirty MLP-up arms without replacing baseline or random rows.
