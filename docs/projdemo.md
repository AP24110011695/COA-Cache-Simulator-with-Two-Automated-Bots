# projdemo.md — How to Run and Demonstrate the COA Cache Simulator

This guide explains, in very simple English, how to run the application,
what every part of the screen does, and how to demonstrate the project to
your teacher.

You do not need to know anything about caches, C++, or "bots" before
reading this. Every technical word is explained the first time it appears.

---

## Quick Start — Run the Project

Do this whenever you want to start the application. (First-time full
setup is explained in Part 1.)

**In VS Code, open the terminal (Git Bash recommended), then run:**

```bash
cd "/c/Projects/COA Cache Simulator with Two Automated Bots"
mingw32-make -C engine all
cd ui
python -m streamlit run app.py
```

Then open **http://localhost:8501** in your browser.
To stop the application, click the terminal and press **Ctrl + C**.

**PowerShell version of the same commands** (the build step is only
tested in Git Bash — see Part 1):

```powershell
cd "C:\Projects\COA Cache Simulator with Two Automated Bots"
mingw32-make -C engine all        # use Git Bash if this fails
cd ui
python -m streamlit run app.py
```

---

## Part 1 — How to Run the Application in VS Code

### Step 1. Open your project folder in VS Code

1. Open VS Code.
2. Click **File → Open Folder…**
3. Choose:
   `C:\Projects\COA Cache Simulator with Two Automated Bots`
4. Click **Select Folder**.

You should see folders like `engine/`, `ui/`, `bots/`, `traces/`, and
`docs/` in the Explorer panel on the left.

### Step 2. Open the VS Code terminal

The terminal is the panel where you type commands.

- Press **Ctrl + `** (the key under the Esc key), **or**
- Click **Terminal → New Terminal** in the top menu.

A panel opens at the bottom of the window.

### Step 3. Choose the right terminal (Windows)

In the top-right corner of the terminal panel there is a small **▾**
arrow next to a **+** button. Click the arrow to pick a shell.

- **Use Git Bash.** This project's build tool (`mingw32-make`) is tested
  and documented to work from Git Bash. The project itself records that
  other shells are untested for the build (see `docs/memory.md`, section 4).
- **PowerShell also works** for the Python commands (installing packages,
  running tests, starting the app). Only the `mingw32-make` build step is
  not tested outside Git Bash.

### Step 4. Know which folder each command needs

| Command | Run it from | Why |
|---|---|---|
| `pip install ...` | Project root | The `requirements*.txt` files live there. |
| `mingw32-make -C engine all` | Project root | `-C engine` tells make to enter `engine/`. |
| `mingw32-make -C engine test` | Project root | Same reason. |
| `python -m pytest tests -q` | Project root | The `tests/` folder lives there. |
| `python -m streamlit run app.py` | **`ui/` folder** | This is the documented launch convention — it makes Streamlit read `ui/.streamlit/config.toml` (the app's theme). |

### Step 5. Install dependencies (first time only, or if missing)

```bash
cd "/c/Projects/COA Cache Simulator with Two Automated Bots"
pip install -r requirements.txt -r requirements-dev.txt
```

PowerShell: same commands, only the `cd` path looks like
`cd "C:\Projects\COA Cache Simulator with Two Automated Bots"`.

This installs everything the project needs: `streamlit` (the app),
`matplotlib` and `pandas` (charts and tables), `pytest` and `jsonschema`
(tests). The C++ side needs no install — its one header file is already
inside the project (`engine/third_party/`).

### Step 6. Build the C++ engine

The real cache simulation is a small C++ program. Build it once (and
again only if you change C++ code):

```bash
cd "/c/Projects/COA Cache Simulator with Two Automated Bots"
mingw32-make -C engine all
```

Success looks quiet — a few `g++` lines and no red text. It creates
`build/cache_sim.exe`.

Optional check that everything is healthy:

```bash
mingw32-make -C engine test      # prints "summary: 729 checks, 0 failures"
python -m pytest tests -q        # prints "135 passed"
```

### Step 7. Start the application

```bash
cd ui
python -m streamlit run app.py
```

### Step 8. Know it started, and open the right URL

The terminal prints something like:

```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://10.x.x.x:8501
```

That text is your success signal. Open **http://localhost:8501** in your
browser (usually it opens by itself). You should see the page title
**"COA Cache Simulator"** with a sidebar on the left called
**"Cache configuration"**.

### Step 9. Stop the application

Click the terminal window and press **Ctrl + C**. The terminal comes back
to normal, and the browser page stops updating.

---

## Part 2 — What Every Part of the Screen Does

The app has one sidebar (left) and four tabs (top):
**Simulator**, **Experiments**, **Automated workflow**, **Help**.

### A. The Sidebar — "Cache configuration"

The sidebar is where you describe the cache you want to study.

A **cache** is a small, fast memory that keeps copies of data the
computer uses often. When the processor reads an address, it first looks
in the cache. Finding it there is a **hit** (fast). Not finding it is a
**miss** (slow — the data must be fetched from main memory).

**"Organization"** — how cache slots are arranged.

- Think of the cache as a parking lot with numbered spots, and every
  memory block as a car.
- **direct**: each car has exactly ONE allowed spot
  (`block number → one spot`). Simple and fast, but two cars that share a
  spot keep kicking each other out.
- **set_associative**: the lot is divided into groups (called **sets**),
  and a car may park in any free spot **inside its group**. Fewer fights.
  **"Associativity"** is the number of spots per group (2 = two ways).
- **fully_associative**: one big group — a car may park anywhere. Most
  freedom, most searching.

**"Capacity (bytes, power of two)"** — total size of the cache
(default 8 bytes). Bigger cache = more spots = usually more hits.

**"Block size (bytes, power of two, 1–128)"** — how many bytes travel
together as one block (default 2). One address loads its whole block, so
nearby addresses often become hits.

**"Associativity (ways, power of two)"** — spots per set. It only
appears for `set_associative`, and the list only shows valid values for
your capacity and block size.

**"Address width (bits, 4–64)"** — how many bits an address has
(default 16). It sets the biggest allowed address
(8 bits → addresses 0–255).

**"Replacement policy"** — when a set is full and a new block must come
in, which old block leaves?

- **LRU** (Least Recently Used): remove the block that was unused for the
  longest time. Like removing the least-watched video from your playlist.
- **FIFO** (First In, First Out): remove the block that arrived first,
  even if you used it recently. Like a queue at a shop counter.
- **RANDOM**: remove a block chosen by a random number generator. To make
  it repeatable, you give it a **seed** (a starting number). Same seed →
  same choices → same results every run.

Notes: for **direct** the policy box is greyed out with the caption
*"Direct-mapped: one line per set, no policy choice."* — with one spot
there is nothing to choose. The **"Random seed"** box appears only when
the policy is RANDOM.

**"Timing assumptions (AMAT)" toggle** (default on) with
**"Hit time (cycles, assumption)"** (default 1.00) and
**"Miss penalty (cycles, assumption)"** (default 20.00) — these are
make-believe speeds used to compute **AMAT** (Average Memory Access
Time):

```
AMAT = hit time + miss rate × miss penalty
```

They are assumptions for the model, not real hardware measurements.
Turn the toggle off and the AMAT card shows "—".

Invalid combinations show a red message immediately, for example if the
block size is bigger than the capacity. Buttons also become disabled
until you fix it.

### B. Simulator tab

This tab answers: *"For this cache and this list of addresses, what
happens on every single access?"*

The list of addresses is called a **trace**.

**"Trace source" (three choices):**

1. **"Bot 1 generator"** — Bot 1 is a small program that writes traces
   for you. Pick a **"Pattern"**:
   - *sequential*: read addresses one after another
     (**"Start address"**, **"Access count"**, **"Byte stride"** — e.g.
     start 0, count 8, stride 4 → 0, 4, 8, 12, 16, 20, 24, 28).
   - *repeated*: read the same address again and again
     (**"Address"**, **"Repetitions"**) — great for showing hits.
   - *conflict*: addresses that all fight for the **same set**
     (**"Distinct blocks (same set)"**, **"Passes"**, **"Target set"**,
     **"Start block"**) — great for showing evictions.
   Then click **"Generate trace"**.
2. **"Manual paste"** — type addresses yourself, one per line. You can
   write decimal (16) or hex (0x10), and `#` starts a comment. Click
   **"Parse & load trace"**.
3. **"Sample file"** — pick a ready-made trace from `traces/`:
   `e1-repeated.json`, `e2-conflict.json`, `e3-lru-vs-fifo.json`, or
   `sequential-100.json`, then click **"Load sample"**.

After loading, a preview shows the trace name, where it came from, how
many addresses it has, and the first 32 addresses.

**"Run simulation" button** (blue, left side of the tab) — starts the
real C++ engine on your trace. It is disabled (grey) until a trace is
loaded and the sidebar config is valid.

**What appears after running:**

- A green line, e.g. *"Simulation complete — 5 accesses, 1 hit (20.00%)."*
- **Seven metric cards**: Accesses, Hits, Misses, Evictions, Hit rate,
  Miss rate, AMAT (cycles).
  - A **hit** means the data was already in the cache — fast.
  - A **miss** means it had to be loaded in — slow.
  - An **eviction** happens when a set is full and an old block is thrown
    out to make room. (Filling an empty slot is NOT an eviction.)
  - **Hit rate** = hits ÷ accesses, shown as a percent.
- **Cumulative hit-rate chart** — a line showing how the running hit rate
  changes from the first access to the last. The dashed line marks 50%.
- **"Event log"** — a table with one row per access:
  `n` (access number), `address`, `block`, `tag`, `index`, `offset`,
  `set`, `way`, `result` (hit/miss), `evicted block`, and `explanation`.
  - Simple meaning: `block` = which chunk of memory, `set`/`way` = the
    parking group and spot, `tag` = the block's ID inside that spot.
  - For a fully-associative cache, `index` shows "—" because there is
    only one set.
  - The table shows up to 500 rows; **"Download all events (CSV)"** saves
    everything.
- **"Cache state"** — the final contents of the cache, one row per set
  and one column per way. Filled cells show `tag X · blk Y`; the green
  cell is the most recently used line. The caption under the grid quotes
  the engine's explanation of the very last access.

Interaction note: the table is a live grid — you can scroll it, sort by
clicking a column, and use its **Search** button. Nothing else on the
page changes when you click inside the table.

If a run fails (for example an address is too big for the address
width), a red **error card** appears with a code like
`E_TRACE_INVALID`, the exact problem, and the value you gave. Your
previous successful results stay on screen — nothing is erased.

### C. Experiments tab

Bot 2 runs **controlled experiments**: same trace, change exactly ONE
thing, compare the results fairly.

You need a trace loaded first (Simulator tab). Otherwise the tab shows a
grey hint and **"Run experiments"** is disabled.

**"Experiment mode" (two choices):**

1. **`policy_comparison`** — keep the cache fixed, compare **LRU vs FIFO
   vs RANDOM**. You must give a **"RANDOM seed"** (already filled with
   12345) so the RANDOM run is repeatable. The seed is recorded in the
   results.
2. **`organization_comparison`** — keep capacity, block size, and trace
   fixed, compare **direct vs set_associative vs fully_associative**.
   Your sidebar organization must be `set_associative` (it supplies the
   associativity), and LRU is used wherever a policy exists.

Restrictions the app enforces (with clear red messages):
policy comparison on a direct-mapped cache is refused (`E_CONFIG_INVALID`
— direct-mapped has no policy to compare); organization comparison
refuses a non-set-associative base config.

Click **"Run experiments"**. What appears:

- **Comparison table** — one row per run: Run number, Policy (or
  Organization), Seed, Hits, Misses, Evictions, Hit rate, AMAT (cycles).
  The best hit rate is shown in **bold**.
- **Grouped bar chart** — green hits, red misses, amber evictions per run.
- **"Summary"** — one plain-English sentence per run plus the conclusion,
  built only from the numbers, e.g. *"Best hit rate: FIFO and RANDOM tie
  at 40.00% (LRU 20.00%)."*
- **"Save report"** — writes the full experiment record into the
  `reports/` folder; the screen shows *"Report saved to …"*. The record
  stores everything needed to repeat the experiment: the trace, all
  configs, the seed, the engine version, and every number.
- **"Download record (JSON)"** — saves the same record as a file.

### D. Automated workflow tab

This tab shows the whole project working by itself with **one click**.

The three players:

- **Bot 1** — writes a trace (here: a conflict trace for your config).
- **The C++ engine** — simulates the trace. It is the only part that
  computes cache behavior; the bots never invent results.
- **Bot 2** — runs the policy comparison on that trace and writes the
  report.

Inputs: **"Conflict blocks"** (default 4), **"Passes"** (default 1),
**"RANDOM seed"** (default 12345). These control Bot 1's trace and the
RANDOM run.

Click **"Run automated workflow"**. Four steps run in order, each with a
live status box and a colored pill:

1. **Trace generation** (Bot 1) → pill **DONE**, message shows the trace
   name (e.g. `conflict-4b-set0-p1`).
2. **Engine simulation** → pill **DONE**, message shows accesses/hits.
3. **Policy comparison** (Bot 2) → pill **DONE**.
4. **Report** → pill **DONE**, shows the saved file path.

Below the pills you get the workflow's own metric cards, comparison
table, summary text, the saved-report caption, and a
**"Download workflow report (JSON)"** button.

If a step fails, its pill turns **FAILED**, a red error card explains
why, earlier finished steps stay visible, and a
**"Retry failed step"** button appears — it re-runs from the failed step
only, keeping the earlier results.

### E. Help tab and other small things

- **Help tab** — short reference inside the app: organizations, policies,
  metric formulas, the resource limits, how to read the views, and the
  list of sample traces. Good to open if your teacher asks a definition.
- **Empty states** — before you run anything, grey cards tell you what is
  missing, e.g. *"No simulation yet. Configure the cache, choose a trace,
  and run."* They are normal, not errors.
- **The "Running…" / Stop banner** (top right) — Streamlit shows a small
  running icon while it works, then it disappears. You rarely touch it.
- **Important demo habit:** do **not** refresh the browser page (F5)
  during a demonstration. A refresh resets the session and clears the
  results on screen. If it happens, simply load the trace and run again —
  the numbers will be identical because everything is deterministic.
- **Changing sidebar values does not re-run anything by itself.** Results
  only change when you press a button. Old results stay until you load a
  new trace or run again.

---

## Part 3 — Step-by-Step Project Demonstration for My Sir

This uses the project's own worked example **E3** — a trace where LRU and
FIFO give **different** results on the same cache. All numbers below are
the project's verified, documented results (see `docs/demo-record.json`).

**One-line story of the demo:** the same five addresses, the same cache,
two replacement policies — and FIFO gets more hits than LRU. That proves
the replacement policy really matters.

### Before your teacher arrives

Run the app (Quick Start), open http://localhost:8501, and do nothing
else. Everything below happens live.

### Step 1 — Introduce the configuration

1. **Action:** point at the sidebar. Set it exactly like this:
   - Organization: `set_associative`
   - Capacity: `8`
   - Block size: `2`
   - Associativity: `2`
   - Address width: `8`  *(type 8 — the default is 16)*
   - Replacement policy: `LRU`
   - Timing assumptions: ON (Hit time 1.00, Miss penalty 20.00)
2. **Expected result:** no red messages; the caption under Organization
   does not appear; the policy box is enabled.
3. **Meaning:** a tiny 8-byte, 2-way set-associative cache with 8-bit
   addresses (0–255) — small enough to check every number by hand.
4. **What I can say:** *"This is a small two-way set-associative cache.
   I set the address width to 8 bits, so addresses go from 0 to 255."*

### Step 2 — Load the demonstration trace

1. **Action:** in the **Simulator** tab, choose "Sample file" under
   Trace source, pick **`e3-lru-vs-fifo.json`**, click **"Load sample"**.
2. **Expected result:** a preview appears — name `e3-lru-vs-fifo`,
   5 addresses: `0, 4, 0, 8, 4`.
3. **Meaning:** three memory blocks (A=0, B=4, C=8) are read in the order
   A, B, A, C, B. All three map to the same set, and the set only has
   two slots.
4. **What I can say:** *"This trace reads block A, then B, then A again,
   then C, then B. All three blocks must share one set with only two
   lines, so the cache is forced to make replacement decisions."*

### Step 3 — Run the LRU simulation

1. **Action:** click **"Run simulation"**.
2. **Expected result:** green line *"Simulation complete — 5 accesses,
   1 hit (20.00%)."* Cards: Accesses 5, Hits 1, Misses 4, Evictions 2,
   Hit rate 20.00%, Miss rate 80.00%, AMAT 17.00 cycles.
3. **Meaning:** only the second read of A (access 3) was a hit. When C
   arrived, LRU removed B (least recently used). When B came back, LRU
   removed A — so B's second read was a miss under LRU.
   AMAT check: 1 + 0.8 × 20 = 17.00 cycles.
4. **What I can say:** *"With LRU we get 1 hit out of 5. The average
   access time is 17 cycles, because 1 + 80% of 20 is 17."*

### Step 4 — Show the event-by-event proof

1. **Action:** scroll to the **Event log**, then the **Cache state** grid.
2. **Expected result:** five rows, each with a plain-language
   `explanation`, e.g. row 4: *"Miss: block 4 loaded into set 0 way 1,
   evicting block 2 (LRU)."* The grid's caption repeats the engine's
   explanation of the last access.
3. **Meaning:** every number on screen comes from the C++ engine, one row
   per access — nothing is made up by the interface.
4. **What I can say:** *"Every access is logged — address, block, tag,
   set, way, and the reason for each decision. The final cache contents
   are shown in the grid."*

### Step 5 — Run the controlled experiment

1. **Action:** open the **Experiments** tab. Mode: `policy_comparison`,
   RANDOM seed: `12345`. Click **"Run experiments"**.
2. **Expected result:** the table shows exactly:

   | Run | Policy | Seed | Hits | Misses | Evictions | Hit rate | AMAT (cycles) |
   |---|---|---|---|---|---|---|---|
   | 1 | LRU | — | 1 | 4 | 2 | 20.00% | 17.00 |
   | 2 | FIFO | — | 2 | 3 | 1 | 40.00% | 13.00 |
   | 3 | RANDOM | 12345 | 2 | 3 | 1 | 40.00% | 13.00 |

   Summary text: *"Best hit rate: FIFO and RANDOM tie at 40.00%
   (LRU 20.00%)."*
3. **Meaning:** same trace, same cache — only the policy changed.
   FIFO wins because its rule ("remove the oldest resident") kept B in
   the cache, and B was read again. LRU's rule removed B right before it
   was needed. The RANDOM run used exactly one random number (seed 12345
   is recorded, so anyone can repeat it and see the same answer).
4. **What I can say:** *"This is a controlled experiment — only one
   thing changes, the replacement policy. FIFO gives 2 hits and AMAT 13
   cycles; LRU gives 1 hit and 17 cycles. So the policy genuinely changes
   performance."*

### Step 6 — Save the report

1. **Action:** click **"Save report"**.
2. **Expected result:** the caption *"Report saved to …reports\exp-…-policy.json"*.
3. **Meaning:** a reproducibility record — trace, all three configs, the
   seed, the engine version, and every number — is written to disk.
4. **What I can say:** *"The experiment saves a record with everything
   needed to repeat it and get the same numbers."*

### Step 7 — Show the one-click automated workflow

1. **Action:** open the **Automated workflow** tab. Leave Conflict
   blocks 4, Passes 1, RANDOM seed 12345. Click
   **"Run automated workflow"**.
2. **Expected result:** four steps turn **DONE** one after another:
   Trace generation → Engine simulation → Policy comparison → Report,
   followed by the workflow's own results and the saved-report path.
3. **Meaning:** Bot 1 builds a conflict trace from your configuration,
   the C++ engine simulates it, and Bot 2 compares the three policies —
   the whole pipeline, no manual steps.
4. **What I can say:** *"Finally, the two bots and the engine work
   together automatically: the trace bot generates a conflict trace, the
   engine simulates it, and the experiment bot compares the policies and
   saves the report."*

### Short speaking script (in your own words)

- **Opening:** *"This is a cache memory simulator. A cache is a small,
  fast memory in front of main memory. I built it to show how the cache
  design and the replacement policy change performance."*
- **Architecture:** *"The simulation itself is a C++ engine — it is the
  single source of truth for every number. Two automated bots prepare the
  work: one generates address traces, the other runs controlled
  experiments. The interface only shows the engine's results."*
- **Main point:** *"On the same trace and the same cache, LRU scored 1
  hit but FIFO scored 2 — same hardware, different policy, different
  speed. And the Random policy is seeded, so results are repeatable."*
- **Closing:** *"Every result can be checked access by access in the
  event log, and every experiment saves a reproducible record. Thank
  you."*

---

## Part 4 — Feature Map

| UI section or feature | What it does | What I click | What I get |
|---|---|---|---|
| Sidebar "Cache configuration" | Describes the cache to simulate | Dropdowns/number boxes | Valid config; red messages if wrong |
| Organization dropdown | Chooses direct / set-associative / fully-associative | "Organization" | Policy box enables/disables; captions explain |
| Capacity, Block size, Associativity | Cache size, chunk size, spots per set | Dropdowns | Derived sets/ways used by the engine |
| Address width | Size of an address (allowed range 0–2ⁿ−1) | Number box | Maximum valid address |
| Replacement policy + Random seed | Which block to evict; seed for RANDOM | Dropdown (+ number box) | Repeatable RANDOM runs |
| Timing toggle + Hit time / Miss penalty | Speed assumptions for AMAT | Toggle + number boxes | AMAT card value (or "—") |
| Trace source: Bot 1 generator | Bot 1 writes a trace | "Generate trace" | Trace preview |
| Trace source: Manual paste | Type your own addresses | "Parse & load trace" | Trace preview, or a red error card |
| Trace source: Sample file | Load a ready trace from `traces/` | "Load sample" | Trace preview |
| "Run simulation" | C++ engine simulates the trace | The blue button | Green summary line, 7 metric cards, chart, event log, cache state |
| Event log | One row per access with explanations | (scroll/sort/search) | Full per-access detail; CSV download |
| Cache state | Final contents per set/way | (view) | Grid + caption of the last access |
| Experiments tab | Bot 2's controlled comparisons | "Run experiments" | Comparison table, bar chart, summary text |
| "Save report" / "Download record (JSON)" | Persist the experiment | The buttons | Saved file in `reports/` + caption |
| Automated workflow tab | Bot 1 → engine → Bot 2 in one click | "Run automated workflow" | Four DONE steps, results, saved report |
| "Retry failed step" | Re-run only the failed step | The button (appears after a failure) | Earlier results kept |
| Help tab | In-app reference | The "Help" tab | Concepts, formulas, limits |

### How the parts connect

```
You (click a button)
        ↓
Streamlit UI (ui/app.py)      — collects your choices, shows results
        ↓
Bot 1 (trace generation)      — writes the address trace
Bot 2 (experiment runner)     — prepares one or more engine runs
        ↓
Engine client (bots/engine_client.py) — talks to the C++ program
        ↓
C++ cache engine (build/cache_sim.exe) — THE simulation: hits, misses,
        evictions, AMAT — the only source of these numbers
        ↓
Results (events, summaries, tables, charts) — rendered by the UI
        ↓
Comparison + saved report (reports/*.json)
```

The Python side never decides hits or misses — it only asks the engine
and displays the answers.

---

## Part 5 — Troubleshooting for Beginners

**The application does not start.**
Check the terminal. You must be in the `ui/` folder when running
`python -m streamlit run app.py`. If you see "can't open file app.py",
run `cd ui` first.

**A Python package is missing** (error like `No module named streamlit`).
From the project root run:
`pip install -r requirements.txt -r requirements-dev.txt`

**The build fails or says mingw32-make is not found.**
Use the **Git Bash** terminal in VS Code (terminal dropdown, top right).
Then from the project root: `mingw32-make -C engine all`. If it still
fails, read the red text — it names the file and the reason.

**The browser page does not open.**
Look at the terminal for the line `Local URL: http://localhost:8501` and
open that address yourself. If the port is busy because an older copy is
still running, press **Ctrl + C** in the old terminal first, then start
again.

**A red error says the engine executable was not found (`E_INTERNAL`,
mentions `mingw32-make`).**
The C++ engine was never built (or `build/` was deleted). Run
`mingw32-make -C engine all` from the project root, then press the
button again.

**A button is grey / disabled.**
"Run simulation" needs a loaded trace. "Run experiments" needs a trace
too. Buttons also disable while the sidebar config is invalid — fix the
red sidebar message first.

**A red error card appears (like `E_CONFIG_INVALID` or
`E_TRACE_INVALID`).**
This is the app working correctly. Read the card: it names the field,
the rule, and the value you gave (e.g. address 300 with width 8 →
maximum is 255). Fix that one thing and press the button again. Your
earlier results are not erased.

**An experiment refuses to run on a direct-mapped cache.**
That is intentional: a direct-mapped cache has one line per set, so
there is no replacement policy to compare. Switch the sidebar
Organization to `set_associative` (or use organization_comparison).

**A workflow step failed.**
Press **"Retry failed step"** — it re-runs from the failed step and
keeps everything that already succeeded. If the trace step itself keeps
failing, check the red card (usually an address outside the width).

**My numbers differ from the guide.**
The results depend on the exact configuration, trace, and seed. The
guide's numbers need: `set_associative`, capacity 8, block 2,
associativity 2, **address width 8**, trace `e3-lru-vs-fifo.json`, seed
12345. A different width, capacity, policy, or seed gives different —
still correct — results.

**I want to run another example / go back.**
You do not need to restart. Just load another trace (or change the
sidebar) and press the button again — new results replace the old ones
on screen. If you accidentally refreshed the browser (results vanished),
simply load the trace and run again; the numbers will be the same.

**The tests, if your teacher asks.**
From the project root: `mingw32-make -C engine test` (729 engine checks)
and `python -m pytest tests -q` (135 tests). Both should end with zero
failures.

---

*Verification note: every button, label, tab, message, and number in
this guide was checked against the application source (`ui/app.py`,
`ui/components.py`, `bots/`), the governing documents in `docs/`, and the
project's archived demonstration evidence (`docs/demo-record.json`,
`docs/phase9-walkthrough.md`). The E3/LRU/FIFO/RANDOM values in Part 3
are the engine's verified output for exactly that configuration. The
only item not executed in this environment is the `mingw32-make` build
from inside PowerShell — use Git Bash for the build step, as the project
itself documents.*
