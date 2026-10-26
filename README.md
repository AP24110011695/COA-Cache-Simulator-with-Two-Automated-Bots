# COA Cache Simulator with Two Automated Bots

An interactive, read-only cache memory simulator for Computer Organization
and Architecture (COA): a C++ engine performs all cache calculations, two
automated software bots generate address traces and run controlled
experiments, and a Streamlit interface visualizes every access. There is no
AI/LLM layer anywhere in this project.

## What it demonstrates

- **Three cache organizations**: direct-mapped, N-way set-associative,
  fully-associative (exact address decomposition into tag / index / offset).
- **Three replacement policies**: LRU, FIFO, and seeded RANDOM
  (`std::mt19937`) — invalid lines always fill before valid lines are
  evicted.
- **Controlled experiments**: one variable changed at a time (policies on a
  fixed cache; organizations on a fixed trace), with reproducible records.
- **Transparency**: a per-access event log with plain-language
  explanations, the final cache state, derived geometry (sets, tag/index/
  offset bit widths), and AMAT from user-supplied timing assumptions.

The engine is the single source of truth for all cache behavior; the Python
layer never re-implements hit/miss or replacement decisions.

## Status

**Delivered** — all ten implementation phases complete. The scripted
browser walkthrough record is `docs/phase9-walkthrough.md`, the archived
§14 demonstration record is `docs/demo-record.json`, and evidence
screenshots live in `docs/screenshots/`.

## Governing documents

All six governing documents live in `docs/`:

| File | Role |
|---|---|
| [docs/prd.md](docs/prd.md) | Scope and acceptance criteria |
| [docs/architecture.md](docs/architecture.md) | Contracts, schemas, worked examples |
| [docs/rules.md](docs/rules.md) | Coding and correctness standards |
| [docs/design.md](docs/design.md) | UI design system |
| [docs/tasks.md](docs/tasks.md) | Ten-phase implementation plan |
| [docs/memory.md](docs/memory.md) | Verified current state (updated every phase) |

## Verified environment

- g++ (MinGW.org GCC-6.3.0-1) 6.3.0 and `mingw32-make` (no CMake, no MSVC);
  build/test commands assume Git Bash (mingw32-make uses `sh` when present)
- Python 3.12 with the packages from `requirements.txt` /
  `requirements-dev.txt` (streamlit, matplotlib, pandas; pytest and
  jsonschema for the tests)

## Setup, build, run, and test

```bash
# 1. Python dependencies
pip install -r requirements.txt -r requirements-dev.txt

# 2. Build the C++ engine (zero-warning gate)
mingw32-make -C engine all          # produces build/cache_sim.exe

# 3. Run every test suite
mingw32-make -C engine test         # 729 engine checks across 17 sections
python -m pytest tests -q           # 135 unit + integration tests

# 4. Launch the UI (from ui/ so ui/.streamlit/config.toml applies)
cd ui && python -m streamlit run app.py
```

The engine can also be exercised directly:

```bash
build/cache_sim.exe --mode version
build/cache_sim.exe --mode geometry --in config.json
build/cache_sim.exe --mode simulate --in job.json
```

Error envelopes use the closed code set `E_USAGE` / `E_JOB_INVALID` /
`E_CONFIG_INVALID` / `E_TRACE_INVALID` / `E_LIMIT` / `E_INTERNAL` with
exit codes 0 / 2 / 3 / 4 (contracts in `docs/architecture.md` §5–§6,
canonical schemas in `schemas/`).

### The 3D Cache Machine

After running a simulation in the Simulator tab, the section **"The Cache
Machine — 3D view"** renders the run as a three-lane 3D diorama: Main
Memory (left), the Address Bus with the decoded address (middle), and the
CPU Cache (right). It replays the engine's own events and per-access
snapshots — hits, misses, line fills, and evictions animate step by step
with Play/Pause/Next/Previous/Replay/Reset, a speed control, and a
scrubber. The view uses the vendored three.js r128 (MIT, `ui/static/`),
works offline, and is available for traces up to 2,000 accesses within
the snapshot budget; larger runs keep the 2D views with an explanatory
caption. The scene displays engine output only — it never computes cache
behavior.

## The controlled demonstration (two-minute walkthrough)

1. Launch the UI and, in the sidebar, choose: organization
   `set_associative`, capacity `8`, block size `2`, associativity `2`,
   address width `8`, policy `LRU`, timing assumptions on (hit time 1,
   miss penalty 20 cycles).
2. Simulator tab → trace source "Sample file" → load
   `e3-lru-vs-fifo.json` → "Run simulation". Expected: **5 accesses,
   1 hit, 4 misses, 2 evictions, 20.00% hit rate, AMAT 17.00 cycles** —
   the trace is `0, 4, 0, 8, 4` (blocks A, B, C in one set; the published
   worked example E3 of `docs/architecture.md` §13).
3. Experiments tab → mode `policy_comparison`, seed `12345` → "Run
   experiments". Expected: LRU 1/4/2 (AMAT 17.00), FIFO 2/3/1 (13.00),
   RANDOM (seed 12345, recorded) 2/3/1 (13.00) — FIFO and RANDOM tie for
   the best hit rate. "Save report" writes the reproducibility record to
   `reports/` (an archived copy is `docs/demo-record.json`).
4. Automated workflow tab → "Run automated workflow" runs Bot 1 (trace
   generation) → the engine → Bot 2 (policy comparison) → report with
   per-step statuses.

Manual traces: one address per line, decimal or `0x` hex, `#` comments;
the bundled samples in `traces/` exist in both formats.

## Resource limits

Traces 0–100,000 addresses; address width 4–64 bits; block size power of
two 1–128 B; capacity power of two up to 1,048,576 B; associativity power
of two 2 up to capacity ÷ block size; RANDOM seed uint32; per-access
state snapshots for traces up to 2,000 addresses **and**
snapshots × total cache lines ≤ 2,000,000; timing inputs are
modeling assumptions in clock cycles — AMAT = hit time + miss rate ×
miss penalty, never a measured latency.

## Repository layout

```
engine/    C++ cache engine (src, include, tests, vendored nlohmann/json)
bots/      trace_bot.py, experiment_bot.py, engine_client.py
ui/        Streamlit app (app.py, components.py, tokens.py, styles.css)
schemas/   canonical JSON schemas for every cross-process contract
traces/    sample traces (json + manual txt)
tests/     pytest suite (unit + integration, imports the built engine)
docs/      governing documents, walkthrough record, screenshots, demo record
reports/   saved experiment records (created on demand)
build/     build output (cache_sim.exe, engine_tests.exe)
```
