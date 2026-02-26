"""
GPU-Accelerated Magic Square of Squares Solver — v5.1 (Engineering Grade)
"The Ghost of the Center"

v5.1 Features:
  - Runs Directory: All artifacts in runs/(N)magic_YYYYMMDD_HHMM/
  - Strict Resume: -resume [ID] fails loud if folder missing.
  - Data-First SCADA UI: Windowed metrics, ETA, and backpressure telemetry.
  - Pipelined: Multithreaded producer (GPU) + Multiprocessing consumer (CPU).
"""

import sys
import time
import itertools
import multiprocessing as mp
import json
import threading
import queue
import argparse
import datetime
import math
from pathlib import Path
from collections import deque
import torch # Move to top for linter

def nCr(n, r):
    if r < 0 or r > n: return 0
    if r == 0 or r == n: return 1
    if r > n // 2: r = n - r
    
    numer = denom = 1
    for i in range(1, r + 1):
        numer = numer * (n - i + 1)
        denom = denom * i
    return numer // denom

# Add local module paths
BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

import magic
import number_pool

# RID Framework Coefficients (Physical Foundation)
EMA_ALPHA = 0.1
TARGET_STABILITY = 1.0

# Initial Hardware Baseline (conservative default to avoid driver resets)
GPU_BATCH_SIZE = 200_000
LOG_INTERVAL = 2.0
SUMMARY_INTERVAL = 60.0
TOTAL_SPACE = nCr(len(magic.numbers), 9)

class RIDGovernor:
    """
    AIOS V2 Dynamic Stability Governor.
    Governs GPU_BATCH_SIZE (Structural Capacity) to hit 100% load safely.
    """
    def __init__(self, initial_batch_size):
        self.batch_size = initial_batch_size
        self.s_n = 1.0
        self.ltp = 1.0 # Structural Capacity (Memory Headroom)
        self.rle = 1.0 # Load Efficiency (Throughput Stability)
        self.history = deque(maxlen=10)

    def step(self, cps_ema, current_cps):
        # 1. Calculate LTP (Structural Support)
        # Ratio of available GPU memory vs total reserved
        if torch.cuda.is_available():
            reserved = torch.cuda.memory_reserved()
            allocated = torch.cuda.memory_allocated()
            free = reserved - allocated
            # LTP = min(1, support/demand). We use normalized memory headroom.
            self.ltp = min(1.0, (free + 1e-6) / (reserved + 1e-6))
        
        # 2. Calculate RLE (Load Efficiency)
        # Jitter in CPS. If current_cps drops significantly below EMA, efficiency is low.
        if cps_ema > 0:
            self.rle = min(1.0, current_cps / cps_ema)
        
        # 3. Compute S_n (Master Stability Scalar)
        # S_n = RSR * LTP * RLE. (RSR assumes 1.0 for compute consistency)
        self.s_n = 1.0 * self.ltp * self.rle
        
        # 4. Adjust Batch Size (Governance)
        if self.s_n < 0.8:
            self.batch_size = int(self.batch_size * 0.8) # Throttle down
            print(f"\n[RID] Stability Alert (S_n: {self.s_n:.4f}) | Throttling to {self.batch_size:,}")
        elif self.s_n >= 0.95 and self.ltp > 0.3:
            self.batch_size = int(self.batch_size * 1.1) # Scale up
            # Limit to 10M to prevent OOM
            self.batch_size = min(self.batch_size, 10_000_000)
        
        return self.batch_size, self.s_n

class SolverMetrics:
    def __init__(self, start_batch=0, total_found=0):
        self.start_timer = time.time()
        self.last_tick_time = self.start_timer
        self.last_summary_time = self.start_timer
        
        self.batches_total = start_batch
        self.batches_since_tick = 0
        self.total_found = total_found
        self.last_tick_combos = start_batch * GPU_BATCH_SIZE
        
        self.gpu_ms_ema = 0.0
        self.cpu_ms_ema = 0.0
        self.cps_ema = 0.0
        self.spm_window = deque(maxlen=200)
        
        # Tick metrics
        self.survivors_since_tick = 0
        self.drained_since_tick = 0
        self.arrangements_since_tick = 0
        
        self.tick_count = 0
        self.eta_str = "Calculating..."

    def update_gpu(self, ms, survivors):
        self.gpu_ms_ema = (ms * EMA_ALPHA) + (self.gpu_ms_ema * (1 - EMA_ALPHA)) if self.gpu_ms_ema > 0 else ms
        spm = survivors / (GPU_BATCH_SIZE / 1_000_000)
        self.spm_window.append(spm)
        self.survivors_since_tick += survivors
        self.batches_total += 1
        self.batches_since_tick += 1

    def update_cpu(self, ms, survivors):
        if ms > 0:
            self.cpu_ms_ema = (ms * EMA_ALPHA) + (self.cpu_ms_ema * (1 - EMA_ALPHA)) if self.cpu_ms_ema > 0 else ms
        self.drained_since_tick += 1
        self.arrangements_since_tick += (survivors * 40320)

    def calculate_tick(self):
        now = time.time()
        dt = now - self.last_tick_time
        if dt <= 0: return 0, 0
        
        current_combos = self.batches_total * GPU_BATCH_SIZE
        d_combos = current_combos - self.last_tick_combos
        cps = d_combos / dt
        self.cps_ema = (cps * EMA_ALPHA) + (self.cps_ema * (1 - EMA_ALPHA)) if self.cps_ema > 0 else cps
        
        self.tick_count += 1
        if self.tick_count > 5 and self.cps_ema > 0:
            rem_combos = TOTAL_SPACE - current_combos
            rem_sec = rem_combos / self.cps_ema
            self.eta_str = str(datetime.timedelta(seconds=int(rem_sec)))
            
        self.last_tick_time = now
        self.last_tick_combos = current_combos
        return cps, dt

class JsonLogger:
    def __init__(self, run_dir):
        self.path = run_dir / "log.jsonl"
        self.results_path = run_dir / "results.txt"
    def log_tick(self, data):
        entry = {"ts": time.time(), "type": "tick", **data}
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    def log_calibration(self, data):
        entry = {"ts": time.time(), "type": "calibration", **data}
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    def log_discovery(self, data):
        entry = {"ts": time.time(), "type": "solution", **data}
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        with open(self.results_path, "a") as f:
            f.write(f"--- SOLUTION FOUND | Batch: {data.get('batch')} ---\n")
            f.write(str(data.get('grid')) + "\n\n")

def setup_run_dir(resume_id=None):
    runs_base = BASE / "runs"
    runs_base.mkdir(exist_ok=True)
    
    if resume_id:
        # Strict Resume Logic
        match = list(runs_base.glob(f"({resume_id})*"))
        if not match:
            print(f"\n[!] ERROR: RUN ID ({resume_id}) NOT FOUND in {runs_base}")
            sys.exit(1)
        run_dir = match[0]
        print(f"[SYSTEM] Resuming Run: {run_dir.name}")
        return run_dir
    else:
        # Fresh Run Logic
        existing = list(runs_base.glob("(*)*"))
        next_idx = 1
        if existing:
            ids = []
            for d in existing:
                try: ids.append(int(d.name.split(')')[0][1:]))
                except: pass
            if ids: next_idx = max(ids) + 1
        
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        run_dir = runs_base / f"({next_idx})magic_{ts}"
        run_dir.mkdir()
        print(f"[SYSTEM] Starting NEW Run Folder: {run_dir.name}")
        return run_dir

def validate_combination(combo_tuple, mode="science"):
    # Permutation Check (The Panner)
    return magic.check_magic(list(combo_tuple), target_center=sum(combo_tuple)//3, mode=mode)

def run_foundation_calibration():
    """
    n=1 Foundation Calibration. 
    Verifies the pipeline using the 1-9 integer set (The Origin).
    """
    print("\n[RID] Starting n=1 Foundation Calibration (The Origin)...")
    import gpu_magic_filter
    calibration_pool = list(range(1, 10))
    combos = list(itertools.combinations(calibration_pool, 9))
    
    survivors = gpu_magic_filter.filter_combinations_gpu(combos)
    found = 0
    for s in survivors:
        if magic.check_magic(list(s), target_center=5, mode="science"):
            found += 1
    
    if found >= 1:
        print(f"[RID] FOUNDATION VERIFIED: {found} base squares identified. S_n = 1.0")
        return True
    else:
        print("[RID] FOUNDATION FAILURE: Pipeline inconsistent.")
        return False

def run_solver():
    parser = argparse.ArgumentParser()
    parser.add_argument("-resume", type=str, help="ID of the previous run to resume")
    parser.add_argument("--cores", type=int, default=16)
    parser.add_argument(
        "--mode",
        type=str,
        default="science",
        choices=["science", "harmonic"],
        help="Search mode: 'science' (strict math) or 'harmonic' (heuristics)",
    )
    parser.add_argument(
        "--power",
        type=int,
        choices=[1, 2, 3],
        help="Override MAGIC_POWER for this run: 1=baseline, 2=squares, 3=cubes.",
    )
    parser.add_argument(
        "--execute-here",
        action="store_true",
        help=(
            "If used with --power 1, run ONLY the n=1 foundation calibration "
            "and exit (no full siege). Other powers ignore this flag."
        ),
    )
    args = parser.parse_args()

    # Optional per-run power override so commands like
    # `... run_solver.py --mode science --power 1 --execute-here`
    # behave as expected.
    if args.power is not None:
        import os

        os.environ["MAGIC_POWER"] = str(args.power)

    # ─── Calibration-Only Fast Exit (n=1) ───
    if args.power == 1 and args.execute_here:
        ok = run_foundation_calibration()
        # Mirror the boolean as a process exit code for scripting, but
        # avoid starting the full GPU/CPU siege.
        sys.exit(0 if ok else 1)

    # ─── Directories ───
    run_dir = setup_run_dir(args.resume)
    state_file = run_dir / "state.json"
    
    batches_processed = 0
    total_found = 0
    if state_file.exists():
        with open(state_file, "r") as f:
            state = json.load(f)
            batches_processed = state.get("batches_processed", 0)
            total_found = state.get("total_found", 0)

    logger = JsonLogger(run_dir)
    
    # ─── Core Logic ───
    import gpu_magic_filter 
    combos = itertools.combinations(magic.numbers, 9)
    items_to_skip = batches_processed * GPU_BATCH_SIZE
    
    if items_to_skip > 0:
        print(f"[SOLVER] Skipping {items_to_skip:,} combinations...")
        deque(itertools.islice(combos, items_to_skip), maxlen=0)

    # ─── Foundation Calibration ───
    foundation_ok = run_foundation_calibration()
    logger.log_calibration(
        {
            "status": "ok" if foundation_ok else "failed",
            "power": getattr(number_pool, "ACTIVE_POWER", None),
            "pool": getattr(number_pool, "POOL_DESCRIPTION", None),
        }
    )
    if not foundation_ok:
        print("[!] Fatal: Foundation calibration failed. Aborting Siege.")
        sys.exit(1)

    metrics = SolverMetrics(batches_processed, total_found)
    governor = RIDGovernor(GPU_BATCH_SIZE)
    tasks = queue.Queue(maxsize=15) # type: ignore
    
    print(f"[SOLVER] Mode: {args.mode.upper()} | Space: {TOTAL_SPACE:,}")
    print(f"[SOLVER] RID Stability Governor Engaged | Baseline: {GPU_BATCH_SIZE:,}")

    # ─── GPU Producer Thread ───
    def producer():
        gen = combos
        while True:
            # Dynamic batch size from governor
            current_batch_size = governor.batch_size
            batch = list(itertools.islice(gen, current_batch_size))
            if not batch:
                tasks.put(None); break
            
            t0 = time.time()
            survivors = gpu_magic_filter.filter_combinations_gpu(batch)
            dt_ms = (time.time() - t0)*1000
            metrics.update_gpu(dt_ms, len(survivors))
            
            tasks.put((metrics.batches_total - 1, survivors, current_batch_size))
            
            if metrics.batches_total % 50 == 0:
                with open(state_file, "w") as f:
                    json.dump(
                        {
                            "batches_processed": metrics.batches_total,
                            "total_found": metrics.total_found,
                            "ts": time.time(),
                            "batch_size": current_batch_size,
                            "power": getattr(number_pool, "ACTIVE_POWER", None),
                            "pool": getattr(number_pool, "POOL_DESCRIPTION", None),
                        },
                        f,
                    )

    threading.Thread(target=producer, daemon=True).start()

    # ─── CPU Consumer Loop ───
    from functools import partial
    validate_func = partial(validate_combination, mode=args.mode)
    
    last_ui = time.time()
    with mp.Pool(args.cores) as pool:
        while True:
            try:
                task = tasks.get(timeout=1.0)
                if task is None: break
                
                b_idx, survivors, current_batch_size = task
                if survivors:
                    t1 = time.time()
                    results = list(pool.imap_unordered(validate_func, survivors, chunksize=max(1, len(survivors)//args.cores)))
                    metrics.update_cpu((time.time() - t1)*1000, len(survivors))
                    
                    found = [r for r in results if r]
                    if found:
                        for grid in found:
                            metrics.total_found += 1
                            print(f"\n[!!!] SOLUTION #{metrics.total_found} FOUND | Batch: {b_idx:,}")
                            magic.print_magic_square(grid)
                            logger.log_discovery({"grid": grid, "batch": b_idx})
                else:
                    metrics.update_cpu(0, 0)

                # UI TICK (Data-First professional)
                now = time.time()
                if now - last_ui > LOG_INTERVAL:
                    cps, dt = metrics.calculate_tick()
                    # Step the Governor
                    new_batch, s_n = governor.step(metrics.cps_ema, cps)
                    
                    uptime = now - metrics.start_timer
                    pct = (metrics.batches_total * governor.batch_size / TOTAL_SPACE) * 100
                    spm_win = sum(metrics.spm_window)/len(metrics.spm_window) if metrics.spm_window else 0
                    
                    print(f"\n[TICK] {time.strftime('%H:%M:%S')} | Up {int(uptime//3600):02}:{int((uptime%3600)//60):02}:{int(uptime%60):02} | S_n: {s_n:.4f}")
                    print(f"  Combos   : {metrics.batches_total * governor.batch_size:,} / {TOTAL_SPACE:,} ({pct:.3f}%)")
                    print(f"  Rate     : {cps/1e6:.2f}M c/s (EMA {metrics.cps_ema/1e6:.2f}M) | Batch: {governor.batch_size:,} | ETA {metrics.eta_str}")
                    print(f"  GPU      : {metrics.gpu_ms_ema:.0f}ms/batch (EMA) | survivors: {metrics.survivors_since_tick} | SPM(200b): {spm_win:.4f}")
                    print(f"  CPU      : drained: {metrics.drained_since_tick} | arr/s: {int(metrics.arrangements_since_tick/dt):,} | ms: {metrics.cpu_ms_ema:.0f} (EMA) | queue: {tasks.qsize()}")
                    
                    logger.log_tick(
                        {
                            "combos": metrics.batches_total * governor.batch_size,
                            "cps": cps,
                            "spm": spm_win,
                            "s_n": s_n,
                            "batch": governor.batch_size,
                            "power": getattr(number_pool, "ACTIVE_POWER", None),
                            "pool": getattr(number_pool, "POOL_DESCRIPTION", None),
                        }
                    )
                    
                    # Reset Tick counters
                    metrics.batches_since_tick = 0
                    metrics.survivors_since_tick = 0
                    metrics.drained_since_tick = 0
                    metrics.arrangements_since_tick = 0
                    last_ui = now

                # PERIODIC SUMMARY
                if now - metrics.last_summary_time > SUMMARY_INTERVAL:
                    print(f"\n--- PERIODIC SUMMARY ({time.strftime('%H:%M:%S')}) ---")
                    print(f"  Run ID: {run_dir.name} | Total Space Cover: {pct:.4f}%")
                    print(f"  Avg Rate: {metrics.cps_ema/1e6:.2f}M c/s | Solutions Found: {metrics.total_found}")
                    metrics.last_summary_time = now

            except queue.Empty: continue

    # Final Save
    with open(state_file, "w") as f:
        json.dump(
            {
                "batches_processed": metrics.batches_total,
                "total_found": metrics.total_found,
                "ts": time.time(),
                "power": getattr(number_pool, "ACTIVE_POWER", None),
                "pool": getattr(number_pool, "POOL_DESCRIPTION", None),
            },
            f,
        )
    print(f"\n[!!!] SEARCH COMPLETE. Data at: {run_dir}")

if __name__ == "__main__":
    mp.freeze_support()
    run_solver()
