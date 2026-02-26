# GPU-Accelerated 3x3 Magic Square of Squares Solver

A self-contained, massively optimized pipeline for searching the legendary **3x3 Magic Square of Squares** — where every row, column, and diagonal consists of distinct perfect squares summing to the same value.

The search space is 3,042,312,350 combinations. A pure CPU approach would take **130 days**. This pipeline uses a PyTorch GPU Probability Funnel to reduce the search space before the CPU ever touches it.

---

## Architecture: Panning for Gold

```
itertools.combinations(numbers, 9)  ← river of ~3B candidate sets
           │
           ▼
┌──────────────────────────────────────┐
│  GPU PHASE A — Combination Filter    │  10,000,000 at a time
│  • sum(combo) % 3 == 0               │  ~7 seconds per batch
│  • magic constant in valid range     │  Eliminates ~66% upfront
└──────────────────┬───────────────────┘
                   │ ~3.36M survivors
                   ▼
┌──────────────────────────────────────┐
│  CPU PHASE B — Permutation + Check   │  16 parallel threads
│  • magic.check_magic(combo)          │  Tries 8! = 40,320     
│  • Full harmonic + phi + curvature   │  arrangements per combo
│  • Root triangle geometry validation │
└──────────────────────────────────────┘
           │
           ▼
    found_squares.txt  (if discovered)
```

**Why this design?**
- The GPU is cheap at set-level math but can't evaluate geometric arrangements. It acts as a **sluice box** — running river water (combinations) through a screen to eliminate obvious gravel.
- The CPU is expensive at permutations but is the only tool for the deep harmonic checks. It only sees the **concentrated candidate pan** after GPU-filtering.
- Scalable: one GPU can feed N CPU machines simultaneously. If you had 2 CPUs, the GPU simply feeds both.

---

## The Math: Harmonic Geometry

The search isn't pure brute force — `magic.py` enforces strict geometric constraints:
- **Parity & Root Triangles**: Grid roots must form geometric mean relationships
- **Harmonic Reflection**: Opposite cross values must mathematically reflect across the center
- **Phi / Delta Tolerance**: Golden ratio and delta tolerance checks across diagonals
- **Curvature Balance**: Row energy (sum of square roots) must be within tight tolerance

---

## Phase 25: Pipeline Contract Fix

> **v1 Bug (now fixed):** The original GPU filter treated sorted combination-tuples as fixed-position grids and checked row/col/diagonal sums directly. Since `itertools.combinations` produces *sorted, unordered* sets, this guaranteed 0 survivors always — not because no magic squares exist, but because the data contract was wrong.

> **v2 Fix:** The GPU filter now performs *permutation-invariant* set-level checks (`sum % 3 == 0`, range bounds) — constraints valid for **any** arrangement of the 9 elements. The CPU then handles full permutation-and-validate.

---

## Requirements
- Python 3.10+
- `torch` (PyTorch with CUDA)
- `numpy`

## Power Modes

The search pool is configured via `number_pool.py` and `power_modes.py`, with
the active **power** selected by the `MAGIC_POWER` environment variable.

- **n = 1 — Foundation (Baseline Integers)**  
  - Pool: `1..9` (used by `run_foundation_calibration()` as the Origin set).  
  - Purpose: Verify the full GPU → CPU pipeline and RID stability on a tiny, known field.

- **n = 2 — Squares (Even Siege)**  
  - Pool: `30^2 .. 80^2`.  
  - Result so far: Run (6) completed an exhaustive negative search — **0 magic squares found** over 3,042,312,350 combinations.

- **n = 3 — Cubes (Odd Siege)**  
  - Pool: `30^3 .. 80^3`.  
  - Design: Same index range as the square siege, but with odd powers.  
  - Status: Siege prepared; odd-power falsification test pending execution.

Internally, the active pool and its description are exposed as:

- `number_pool.ACTIVE_POWER` — current power `n`.  
- `number_pool.POOL_DESCRIPTION` — human-readable description (e.g. `"Cubes (30^3 to 80^3)"`).

RID telemetry and run state snapshots now include these fields for every siege.

---

## Run (Safe Siege Pattern)
**Important:** Running the full siege directly from an IDE can be unstable on
some setups. The recommended pattern is to run from your own terminal, with
the power selected via `MAGIC_POWER` or the `magic_runner.py` helper.

### Using `magic_runner.py` (recommended)

From the `Sqaures/Magic_Complete` directory:

```bash
python magic_runner.py --power 3 --mode science --cores 16
```

This **does not** auto-start the siege. Instead, it prints platform-specific
commands you can copy-paste into your own terminal (PowerShell, cmd.exe, or a
POSIX shell) with the correct `MAGIC_POWER` and `run_solver.py` arguments.

Example (PowerShell, n=3 cubes, science mode):

```powershell
cd l:\Steel_Brain\Sqaures\Magic_Complete
$env:MAGIC_POWER="3"; python run_solver.py --mode science --cores 16
```

### Direct `run_solver.py` usage (advanced)

If you prefer to bypass `magic_runner.py`, you can set `MAGIC_POWER` yourself
and call the solver directly:

```powershell
cd l:\Steel_Brain\Sqaures\Magic_Complete
$env:MAGIC_POWER="3"; python run_solver.py --mode science --cores 16
```

The solver will:

- Run the **n=1 foundation calibration** first (using the 1–9 baseline set).  
- Engage the **RID governor** to dynamically tune GPU batch size for stability.  
- Log ticks and calibration metadata (including `power` and `pool`) to
  `runs/(N)magic_YYYYMMDD_HHMM/log.jsonl` and `state.json`.

