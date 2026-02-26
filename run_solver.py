import sys
import time
import itertools
import multiprocessing as mp
import json
import os
from pathlib import Path

# Local imports
import magic
import gpu_magic_filter

STATE_FILE = Path(r"hunting_magic_state.json")
# GPU can effortlessly crunch matrix math on 10 million grids at once
GPU_BATCH_SIZE = 10000000 

def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                return state.get("chunks_processed", 0), state.get("total_found", 0)
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

def run_solver():
    print("\n========================================================")
    print("  GPU-ACCELERATED MAGIC SQUARES SOLVER")
    print("========================================================")
    
    # Setup combinatorial generator
    magic.print_magic_square_principles()
    combos = itertools.combinations(magic.numbers, 9)
    
    chunks_processed, total_found = load_state()
    items_to_skip = chunks_processed * GPU_BATCH_SIZE
    
    if items_to_skip > 0:
        print(f"\n[SOLVER] Resuming from previous state: Skipping {items_to_skip:,} checked permutations...")
        # Fast-forward the generator in C-speed
        next(itertools.islice(combos, items_to_skip, items_to_skip), None)
        print("[SOLVER] Generator sequence restored.")
    else:
        print("\n[SOLVER] Starting fresh 23-billion permutation search.")
        
    print("[SOLVER] Engaging PyTorch GPU Tensor Filter -> CPU Worker cluster...\n")
    time.sleep(2)
    
    # 16 threads for standard hardware
    cores_to_use = 16 
    
    with mp.Pool(cores_to_use) as pool:
        while True:
            # == WORKLOAD EXECUTION ==
            # GPU loads 10 Million items at once
            chunk = list(itertools.islice(combos, GPU_BATCH_SIZE))
            if not chunk:
                print("\n[!!!] COMBINATORIAL SPACE EXHAUSTED. SEARCH COMPLETE.")
                break
                
            batch_num = chunks_processed * GPU_BATCH_SIZE
            print(f"[{time.strftime('%H:%M:%S')}] Target: {batch_num:,} permutations...")
                
            # Execute Phase 24 PyTorch Filter
            gpu_start = time.time()
            cpu_workloads = gpu_magic_filter.filter_permutations_gpu(chunk)
            gpu_ms = (time.time() - gpu_start) * 1000
            
            total_survivors = sum(len(w) for w in cpu_workloads)
            print(f"   └── [GPU] Crushed {len(chunk):,} combos into {total_survivors:,} geometric survivors in {gpu_ms:.1f}ms")
            
            # If nothing survived the GPU, skip the CPU loop
            if total_survivors > 0:
                check_partial = magic.partial(magic.check_magic, target_center=None, delta_tol=18, phi_tol=0.05)
                
                # Execute on the 16 CPU hardware threads. cpu_workloads is a list of lists, so we chain.
                flattened_survivors = itertools.chain.from_iterable(cpu_workloads)
                # Since chunksize=1 here, each hit is processed.
                results = list(pool.imap_unordered(check_partial, flattened_survivors))
                
                for res in results:
                    if res:
                        total_found += 1
                        print("\n" + "="*50)
                        print(f"*** 3D MAGIC SQUARE GEOMETRY FOUND (#{total_found}) ***")
                        print("="*50)
                        magic.print_magic_square(res)
                        magic.export_grid(res, filename=r"found_squares.txt")
                    
            chunks_processed += 1
            save_state(chunks_processed, total_found)

if __name__ == "__main__":
    mp.freeze_support()
    run_solver()
