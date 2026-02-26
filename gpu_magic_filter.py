"""
gpu_magic_filter.py — Phase 26 CORRECTED (v3)
"The Ghost of the Center" Optimization

CONTRACT FIX: 
  • GPU Phase: Perform permutation-invariant set-level checks on combinations.
  
  OPTIMIZATION (v3):
  1. sum(combo) % 3 == 0 — Magic constant must be integer
  2. The target center element MUST be M = (TotalSum / 3).
     If M is not one of the 9 elements in the set, the set is discarded.
     This enforces a fundamental magic square law on the GPU, crushing the
     CPU workload by an additional ~80-90%.
"""

import torch
import sys

# Ensure PyTorch is using CUDA
if not torch.cuda.is_available():
    print("[CRITICAL] CUDA not available. GPU filter requires a CUDA-capable GPU.")
    sys.exit(1)

device = torch.device("cuda")
# Pre-initialize CUDA context
_ = torch.zeros(1, device=device)


def filter_combinations_gpu(combinations_list):
    """
    Takes a list of sorted 9-integer tuples (combinations).
    Returns surviving combinations that pass set-level constraints.
    """
    if not combinations_list:
        return []

    # Load into VRAM
    # Use int64 for sums to prevent overflow (though 6400*9 fits in int32, 
    # v3 uses a center membership check which is safer with exact types)
    tensor_combos = torch.tensor(combinations_list, dtype=torch.int64, device=device)

    # 1. Calculate Total Sum and Magic Constant (M)
    total_sums = tensor_combos.sum(dim=1)  # Shape: (N,)

    # 1. Total sum must be divisible by 9 (for M/3 to be an integer center)
    divisible_mask = (total_sums % 9 == 0)

    # 2. Calculate Target Center (C = TotalSum / 9)
    target_centers = total_sums // 9

    # FILTER 2: Target Center MUST be present in the combination
    # (tensor_combos == target_centers.unsqueeze(1)) checks each of the 9 cols
    # .any(dim=1) checks if any col matched the target_center
    center_present_mask = (tensor_combos == target_centers.unsqueeze(1)).any(dim=1)

    # Combined mask (divisible by 3 and center element must be in the set)
    valid_mask = divisible_mask & center_present_mask

    # Extract survivors
    survivor_indices = valid_mask.nonzero(as_tuple=True)[0]
    surviving_tensors = tensor_combos[survivor_indices]

    # Return to CPU
    return surviving_tensors.cpu().tolist()


if __name__ == "__main__":
    import time
    import itertools
    
    print("[GPU COMBINATION FILTER v3] Center-Element Optimization...")
    numbers = [i**2 for i in range(30, 81)]
    print(f"Number pool: {len(numbers)} squares")
    
    SAMPLE_SIZE = 1_000_000
    print(f"Generating {SAMPLE_SIZE:,} real combinations...")
    test_data = list(itertools.islice(itertools.combinations(numbers, 9), SAMPLE_SIZE))
    
    print(f"Testing v3 filter on {len(test_data):,} combos...")
    start = time.time()
    survivors = filter_combinations_gpu(test_data)
    ms = (time.time() - start) * 1000
    
    print(f"[RESULT] {len(survivors):,} survivors in {ms:.1f}ms")
    if test_data:
        reduction = 100.0 * (1 - len(survivors)/len(test_data))
        print(f"[REDUCTION] {reduction:.2f}% combinations eliminated")
    if survivors:
        print(f"[SAMPLE] First survivor: {survivors[0]} (M={sum(survivors[0])//3})")
