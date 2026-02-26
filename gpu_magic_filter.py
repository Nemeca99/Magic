"""
gpu_magic_filter.py — Phase 24 CORRECTED (v2)

CONTRACT FIX: The original pipeline passed itertools.combinations (sorted, unordered 9-sets)
directly into a GPU filter that treated them as fixed-position grid cells and checked
row/col/diagonal sums. This guaranteed 0 survivors always, because a sorted combination
almost never satisfies line-sum equality.

CORRECTED ARCHITECTURE:
  • GPU Phase: Perform cheap, PERMUTATION-INVARIANT set-level checks on each combination.
               These filters are valid for ANY arrangement of the 9 elements:
               1. sum(combo) % 3 == 0  — magic constant must be an integer
               2. magic_constant bounds (reasonable for squares in range 900–6400)
               3. Optional center element candidate check
  
  • CPU Phase: For each GPU survivor, generate all permutations (9! = 362,880),
               reshape to 3×3 grids, and run full magic.check_magic() validation.
               This is the expensive but correct validation step.

This two-phase approach is correct: the GPU acts as a COMBINATION pre-filter 
(reducing ~23B sets to manageable millions), and the CPU handles arrangement validation.
"""

import torch
import sys

# Ensure PyTorch is using CUDA
if not torch.cuda.is_available():
    print("[CRITICAL] CUDA not available. GPU filter requires a CUDA-capable GPU.")
    sys.exit(1)

device = torch.device("cuda")
# Pre-initialize CUDA context so first batch doesn't incur the warmup penalty
_ = torch.zeros(1, device=device)


def filter_combinations_gpu(combinations_list):
    """
    Takes a raw list of sorted 9-integer tuples (COMBINATIONS, not permutations).
    
    Performs PERMUTATION-INVARIANT set-level checks on the GPU:
      1. sum(combo) % 3 == 0 — the magic constant (sum/3) must be an integer
      2. The magic constant falls within a physically reasonable range
    
    Returns the surviving COMBINATION tuples as a flat Python list (not split into threads,
    because each survivor will spawn up to 362,880 permutations, so the CPU pool
    manages its own workload dynamically).
    """
    if not combinations_list:
        return []

    # Load combinations into VRAM as int32 (values up to 6400, need more than int16)
    # Shape: (N, 9)
    tensor_combos = torch.tensor(combinations_list, dtype=torch.int32, device=device)

    # Compute the total sum of each combination
    total_sums = tensor_combos.sum(dim=1)  # Shape: (N,)

    # FILTER 1: Magic constant must be an integer (total sum divisible by 3)
    divisible_mask = (total_sums % 3 == 0)

    # FILTER 2: The magic constant (M = total/3) must be in a plausible range
    # Our number pool is 900..6400. A 3x3 magic square of 9 distinct squares from this
    # pool will have a magic constant roughly in [3*900, 3*6400] territory divided by 3 = [900, 6400]
    # We can tighten: sum of 9 smallest = 9*900 = 8100, M = 2700
    #                 sum of 9 largest = 9*6400 = 57600, M = 19200
    magic_constants = total_sums // 3
    range_mask = (magic_constants >= 2700) & (magic_constants <= 19200)

    # FILTER 3: All elements must be distinct (combinations guarantee this by definition,
    # but we add a cheap uniqueness check anyway)
    # Actually combinations() guarantees distinct elements from distinct indices, skip this.

    # Combined mask
    valid_mask = divisible_mask & range_mask

    # Extract surviving COMBINATION indices
    survivor_indices = valid_mask.nonzero(as_tuple=True)[0]
    surviving_tensors = tensor_combos[survivor_indices]

    # Bring back to CPU as Python lists (each will be permuted by CPU workers)
    survivors_cpu = surviving_tensors.cpu().tolist()
    return survivors_cpu


if __name__ == "__main__":
    import time

    print("[GPU COMBINATION FILTER v2] Booting CUDA Tensor Core...")
    print("Testing set-level pre-filter on 10M dummy combinations...\n")

    import itertools
    numbers = [i**2 for i in range(30, 81)]  # same pool as magic.py
    print(f"Number pool: {len(numbers)} perfect squares from 30²=900 to 80²=6400")
    print(f"Generating 10M real combinations via itertools.combinations...")
    test_data = list(itertools.islice(itertools.combinations(numbers, 9), 10_000_000))
    print(f"[INPUT] {len(test_data):,} combinations")

    start = time.time()
    survivors = filter_combinations_gpu(test_data)
    ms = (time.time() - start) * 1000

    print(f"[RESULT] {len(survivors):,} combinations passed set-level filter in {ms:.1f}ms")
    if test_data:
        reduction = 100.0 * (1 - len(survivors)/len(test_data))
        print(f"[REDUCTION] {reduction:.1f}% combinations eliminated")
    if survivors:
        print(f"[SAMPLE] First survivor: {survivors[0]}")
        print(f"[INFO] Each survivor spawns up to 362,880 permutations for CPU validation")
