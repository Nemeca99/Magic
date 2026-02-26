"""
GPU-Accelerated Magic Square of Squares Solver — v3 (Phase 27 Hardened)
"The Ghost of the Center"

Pipeline:
  1. GPU Phase (The Sluice Box): Filter combinations from itertools.combinations
     using PERMUTATION-INVARIANT set-level checks:
     - sum(combo) % 3 == 0 (Magic Constant M must be integer)
     - M must be present in the 9-number set (Center Check)
     - Range bounds
     Eliminates 99.99% of combinations in milliseconds.

  2. CPU Phase (The Panners): Each survivor is passed to magic.check_magic(), 
     which handles internal permutations (9 × 8! = 362,880 per center choice)
     and full geometric validation.

Terminology:
  - Combinations: The unordered sets of 9 numbers (C(51,9) ≈ 2.16 Billion).
  - Arrangements: The ordered permutations of those sets (Trillions).
  - Batches: Chunks of 1,000,000 combinations processed at a time.
"""

import sys
import time
import itertools
import multiprocessing as mp
import json
from pathlib import Path
from collections import deque

# Add local module paths
BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

import magic
import gpu_magic_filter

STATE_FILE = BASE / "hunting_magic_state.json"
GPU_BATCH_SIZE = 1_000_000  # 1M is stable for VRAM and RAM overhead

def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                s = json.load(f)
                return s.get("batches_processed", 0), s.get("total_found", 0)
        except Exception:
            pass
    return 0, 0

def save_state(batches_processed, total_found):
    with open(STATE_FILE, "w") as f:
        json.dump({
            "batches_processed": batches_processed,
            "total_found": total_found,
            "timestamp": time.time()
        }, f, indent=4)


def validate_combination(combo_tuple):
    """
    CPU Worker: Receives a flat sorted combination of 9 perfect squares.
    """
    return magic.check_magic(list(combo_tuple), target_center=None, delta_tol=18, phi_tol=0.05)


def run_solver(cores=16):
    print("\n========================================================")
    print("  GPU-ACCELERATED MAGIC SQUARES SOLVER (v3 — Hardened)")
    print("  Pipeline: GPU Combination Filter → CPU Arrangement Check")
    print("========================================================\n")

    combos = itertools.combinations(magic.numbers, 9)
    batches_processed, total_found = load_state()
    items_to_skip = batches_processed * GPU_BATCH_SIZE

    if items_to_skip > 0:
        print(f"[SOLVER] Resuming from state: skipping {items_to_skip:,} combinations...")
        deque(itertools.islice(combos, items_to_skip), maxlen=0)
        print("[SOLVER] Generator restored.\n")
    else:
        print(f"[SOLVER] Starting fresh. Number pool: {len(magic.numbers)} perfect squares")
        print(f"[SOLVER] Total search space: C({len(magic.numbers)},9) ≈ 2,162,693,175 combinations\n")

    print(f"[SOLVER] GPU batch size : {GPU_BATCH_SIZE:,} combinations")
    print(f"[SOLVER] CPU workers    : {cores} threads\n")
    time.sleep(1)

    with mp.Pool(cores) as pool:
        while True:
            # === PHASE A: GPU COMBINATION PRE-FILTER ===
            batch = list(itertools.islice(combos, GPU_BATCH_SIZE))
            if not batch:
                print("\n[!!!] COMBINATORIAL SPACE EXHAUSTED. SEARCH COMPLETE.")
                break

            batch_idx = batches_processed * GPU_BATCH_SIZE
            print(f"[{time.strftime('%H:%M:%S')}] Combinations evaluated: {batch_idx:,}")

            t0 = time.time()
            gpu_survivors = gpu_magic_filter.filter_combinations_gpu(batch)
            gpu_ms = (time.time() - t0) * 1000
            survivor_count = len(gpu_survivors)
            pct = 100.0 * (1 - survivor_count / len(batch))
            print(f"   [GPU] {len(batch):,} → {survivor_count:,} set-survivors in {gpu_ms:.0f}ms ({pct:.2f}% eliminated)")

            # === PHASE B: CPU PERMUTATION + VALIDATION ===
            if survivor_count > 0:
                t1 = time.time()
                cs = max(1, survivor_count // cores)
                results = list(pool.imap_unordered(validate_combination, gpu_survivors, chunksize=cs))
                cpu_ms = (time.time() - t1) * 1000

                hits = [grid for r in results if r for grid in (r if isinstance(r, list) else [r])]
                
                if hits:
                    for grid in hits:
                        total_found += 1
                        print("\n" + "=" * 50)
                        print(f"*** 3D MAGIC SQUARE GEOMETRY FOUND (#{total_found}) ***")
                        print("=" * 50)
                        magic.print_magic_square(grid)
                        magic.export_grid(grid, filename=str(BASE / "found_squares.txt"))

                print(f"   [CPU] Validated {survivor_count:,} candidates ({362880 * survivor_count:,} arrangements) in {cpu_ms:.0f}ms")

            batches_processed += 1
            save_state(batches_processed, total_found)


if __name__ == "__main__":
    mp.freeze_support()
    run_solver(cores=16)
