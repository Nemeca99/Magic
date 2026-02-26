# GPU-Accelerated 3x3 Magic Square of Squares Solver

A self-contained, massively optimized pipeline for searching the legendary **3x3 Magic Square of Squares** — where every row, column, and diagonal consists of distinct perfect squares summing to the same value.

The search space is ~2.3 billion combinations. A pure CPU approach would take **130 days**. This pipeline uses a PyTorch GPU Probability Funnel to reduce the search space before the CPU ever touches it.

---

## Architecture: Panning for Gold

```
itertools.combinations(numbers, 9)  ← river of 2.3B candidate sets
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
│  • magic.check_magic(combo)          │  Tries 9 × 8! = 362,880
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

## Run
```bash
python run_solver.py
```

Progress auto-saves to `hunting_magic_state.json` — interrupt and resume at any time.
