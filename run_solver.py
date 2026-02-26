"""
GPU-Accelerated Magic Square of Squares Solver — v2 (Phase 25 Contract Fix)

Pipeline:
  1. GPU Phase (Combination Filter): Filter sorted 9-tuples from itertools.combinations
     using PERMUTATION-INVARIANT set-level checks (sum divisibility, range bounds).
     Eliminates ~66% of impossible combinations in seconds.

  2. CPU Phase (Permutation + Validation): Each GPU-surviving combination is passed to
     magic.check_magic(), which internally tries all permutations (9 × 8! = 362,880
     arrangements per center element) and runs full geometric validation.

This is the "panning for gold" architecture:
  - The GPU is the sluice box — cheap upfront elimination of impossible sets
  - The CPU pool is the gold panners — expensive but correct geometry verification
  - Scalable: one GPU can feed N CPU pools in parallel
"""

import sys
import time
import itertools
import multiprocessing as mp
import json
from pathlib import Path

# Add local module paths
BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

import magic
import gpu_magic_filter

STATE_FILE = BASE / "hunting_magic_state.json"
GPU_BATCH_SIZE = 10_000_000  # 10M combinations per GPU batch

def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                s = json.load(f)
                return s.get("chunks_processed", 0), s.get("total_found", 0)
        except Exception:
            pass
    return 0, 0

def save_state(chunks_processed, total_found):
    with open(STATE_FILE, "w") as f:
        json.dump({
            "chunks_processed": chunks_processed,
            "total_found": total_found,
            "timestamp": time.time()
        }, f, indent=4)


def validate_combination(combo_tuple):
    """
    CPU Worker: Receives a flat sorted combination of 9 perfect squares.
    Delegates to magic.check_magic() which:
      - Tries every element as the center (9 choices)
      - Permutes remaining 8 elements (8! = 40,320 each)
      - Builds the 3x3 grid and runs full harmonic + geometric checks
    Returns the valid grid tuple if found, else None.
    """
    return magic.check_magic(list(combo_tuple), target_center=None, delta_tol=18, phi_tol=0.05)


def run_solver(cores=16):
    print("\n========================================================")
    print("  GPU-ACCELERATED MAGIC SQUARES SOLVER (v2 — Corrected)")
    print("  Pipeline: GPU Combination Filter → CPU Permutation Check")
    print("========================================================\n")

    combos = itertools.combinations(magic.numbers, 9)
    chunks_processed, total_found = load_state()
    items_to_skip = chunks_processed * GPU_BATCH_SIZE

    if items_to_skip > 0:
        print(f"[SOLVER] Resuming from state: skipping {items_to_skip:,} combinations...")
        next(itertools.islice(combos, items_to_skip, items_to_skip), None)
        print("[SOLVER] Generator restored.\n")
    else:
        print(f"[SOLVER] Starting fresh. Number pool: {len(magic.numbers)} perfect squares")
        print(f"[SOLVER] Total search space: C({len(magic.numbers)},9) ≈ {len(magic.numbers)**9 // 362880:,} combinations\n")

    print(f"[SOLVER] GPU batch size : {GPU_BATCH_SIZE:,} combinations")
    print(f"[SOLVER] CPU workers    : {cores} threads\n")
    time.sleep(1)

    with mp.Pool(cores) as pool:
        while True:
            # === PHASE A: GPU COMBINATION PRE-FILTER ===
            chunk = list(itertools.islice(combos, GPU_BATCH_SIZE))
            if not chunk:
                print("\n[!!!] SEARCH COMPLETE. All combinations evaluated.")
                break

            batch_idx = chunks_processed * GPU_BATCH_SIZE
            print(f"[{time.strftime('%H:%M:%S')}] Batch {chunks_processed+1} | Start: {batch_idx:,}")

            t0 = time.time()
            gpu_survivors = gpu_magic_filter.filter_combinations_gpu(chunk)
            gpu_ms = (time.time() - t0) * 1000
            survivor_count = len(gpu_survivors)
            pct = 100.0 * (1 - survivor_count / len(chunk))
            print(f"   [GPU] {len(chunk):,} → {survivor_count:,} survivors in {gpu_ms:.0f}ms ({pct:.1f}% eliminated)")

            # === PHASE B: CPU PERMUTATION + VALIDATION ===
            if survivor_count > 0:
                t1 = time.time()
                cs = max(1, survivor_count // cores)
                results = list(pool.imap_unordered(validate_combination, gpu_survivors, chunksize=cs))
                cpu_ms = (time.time() - t1) * 1000

                hits = [r for r in results if r is not None]
                print(f"   [CPU] {survivor_count:,} candidates validated in {cpu_ms:.0f}ms | Hits: {len(hits)}")

                for grid in hits:
                    total_found += 1
                    print("\n" + "=" * 50)
                    print(f"  *** MAGIC SQUARE OF SQUARES FOUND (#{total_found}) ***")
                    print("=" * 50)
                    magic.print_magic_square(grid)
                    magic.export_grid(grid, filename=str(BASE / "found_squares.txt"))

            chunks_processed += 1
            save_state(chunks_processed, total_found)


if __name__ == "__main__":
    mp.freeze_support()
    run_solver(cores=16)
