import torch
import time
import sys

# Ensure PyTorch is using CUDA
if not torch.cuda.is_available():
    print("[CRITICAL] CUDA not available. Phase 24 requires a GPU.")
    sys.exit(1)

device = torch.device("cuda")
# Force CUDA initialization now so the first real batch doesn't incur the warmup penalty
_ = torch.zeros(1, device=device)

def filter_permutations_gpu(permutations_list, batch_size=1000000):
    """
    Takes a raw list of 9-integer tuples (permutations).
    Converts them to a PyTorch tensor on the GPU.
    Runs matrix addition across rows, columns, and diagonals.
    Returns the surviving candidates split symmetrically for 16 CPU threads.
    """
    if not permutations_list:
        return []

    # 1. Load the universe into VRAM
    # Shape: (N, 9)
    tensor_perms = torch.tensor(permutations_list, dtype=torch.short, device=device)
    total_perms = tensor_perms.shape[0]
    
    # 2. Extract columns for vectorized math
    # Grid:
    # c0 c1 c2
    # c3 c4 c5
    # c6 c7 c8
    c0, c1, c2 = tensor_perms[:, 0], tensor_perms[:, 1], tensor_perms[:, 2]
    c3, c4, c5 = tensor_perms[:, 3], tensor_perms[:, 4], tensor_perms[:, 5]
    c6, c7, c8 = tensor_perms[:, 6], tensor_perms[:, 7], tensor_perms[:, 8]

    # Calculate the target sum for each grid (Sum of row 0)
    target_sums = c0 + c1 + c2

    # 3. The Logic Filter
    # A true Magic Square must have all rows, columns, and diagonals equal to the target_sum.
    # We use bitwise AND (&) to chain conditions on the GPU.
    valid_mask = (
        (target_sums % 3 == 0) & # Hardware-level absolute sum check (Magic Constant must be integer)
        (c3 + c4 + c5 == target_sums) &  # Row 1
        (c6 + c7 + c8 == target_sums) &  # Row 2
        (c0 + c3 + c6 == target_sums) &  # Col 0
        (c1 + c4 + c7 == target_sums) &  # Col 1
        (c2 + c5 + c8 == target_sums) &  # Col 2
        (c0 + c4 + c8 == target_sums) &  # Diag 1
        (c2 + c4 + c6 == target_sums)    # Diag 2
    )

    # 4. Extract Survivors
    survivor_indices = valid_mask.nonzero(as_tuple=True)[0]
    surviving_tensors = tensor_perms[survivor_indices]
    
    # Bring the surviving data back to the CPU as standard Python lists
    survivors_cpu = surviving_tensors.cpu().tolist()
    survivor_count = len(survivors_cpu)
    
    # 5. Delegate to the 16 hardware threads
    if survivor_count == 0:
        return []

    # We want to split the survivors into 16 distinct arrays for the CPU mp.Pool
    threads = 16
    chunk_size = max(1, survivor_count // threads)
    
    delegated_workloads = []
    for i in range(threads):
        start = i * chunk_size
        # The last thread picks up any remainder
        end = (i + 1) * chunk_size if i < threads - 1 else survivor_count
        if start < survivor_count:
            delegated_workloads.append(survivors_cpu[start:end])

    return delegated_workloads

if __name__ == "__main__":
    # Test harness
    print("[HEPT-UNIT GPU FILTER] Booting Tensor Core...")
    test_data = [
        (8, 1, 6, 3, 5, 7, 4, 9, 2), # Valid 3x3 normal magic square
        (1, 2, 3, 4, 5, 6, 7, 8, 9), # Invalid
        (2, 7, 6, 9, 5, 1, 4, 3, 8)  # Valid 3x3
    ] * 3333333 # ~10 Million items
    
    print(f"[INPUT] Feeding {len(test_data):,} permutations to VRAM...")
    
    start = time.time()
    workloads = filter_permutations_gpu(test_data)
    ms = (time.time() - start) * 1000
    
    total_survivors = sum(len(w) for w in workloads)
    print(f"[RESULT] Extracted {total_survivors:,} geometric survivors in {ms:.2f} ms.")
    print(f"[PIPELINE] Delegated survivors across {len(workloads)} CPU threads.")
