---
name: alice-vllm-deploy
description: Guide deployment and execution of vLLM-based VLM inference on ALICE HPC (or similar SLURM clusters). Covers code and data syncing, venv and model weight verification, SLURM job configuration, the two-phase vLLM server pattern, partition selection, cold start troubleshooting, and SSH discipline. Use when (1) deploying a vLLM-based pipeline to a SLURM cluster, (2) configuring a SLURM job for GPU inference with vLLM, (3) troubleshooting vLLM server startup or timeout issues, (4) choosing between GPU partitions on ALICE, (5) syncing code and data to ALICE via SSH, (6) monitoring a running SLURM job without getting locked out, or (7) setting up vLLM for the first time on an HPC cluster.
argument-hint: "[describe your model, cluster, and what you need to deploy]"
---

# Deploying vLLM on ALICE HPC

## Instructions

### 1. Pre-Deployment Checklist

- **Verify model weights are cached.** On ALICE, HuggingFace models must be pre-downloaded to `/zfsstore/` because compute nodes have no internet access. Check with `ls /zfsstore/user/<username>/.hf_cache/hub/models--<org>--<model>/`. If missing, download on the login node: `HF_HOME=/zfsstore/user/<username>/.hf_cache huggingface-cli download <model>`.
- **Verify vLLM is installed.** Check for the venv: `ls <venv>/lib/python3.12/site-packages/vllm/__init__.py`. Do NOT `import vllm` on the login node — it hangs without a GPU. Verify via file existence only.
- **Install additional dependencies into the vLLM venv.** If your pipeline needs packages not bundled with vLLM (e.g., PyMuPDF for PDF processing), install them: `<venv>/bin/python -m pip install PyMuPDF`. These pure-Python packages won't break the torch/vLLM installation.
- **Sync code and data.** Use `rsync -avz` to transfer pipeline scripts and source data to ALICE. Generate a separate manifest with ALICE paths (replace local paths with `/zfsstore/` paths). Verify with `find <dir> -name '*.pdf' | wc -l`.
- **Create required directories.** The SLURM script needs `logs/` and output directories to exist before submission: `mkdir -p pipeline/logs ocr_output/`.

### 2. The Two-Phase vLLM SLURM Pattern

The pattern used in the GEI textbooks and Webtoon projects:

```
Phase 1: Start vLLM server in background
    ↓ (health check loop waits for /health endpoint)
Phase 2: Run client script against localhost API
    ↓ (processes all pages)
Phase 3: Kill server, run CPU-only post-processing
```

- **Why a server, not direct model loading?** vLLM with `--quantization gptq_marlin` handles GPTQ MoE models reliably. Direct transformers loading with BitsAndBytes NF4 is incompatible with MoE models on transformers v5 (bitsandbytes #1849). Direct GPTQ loading has backend compilation issues. The vLLM server abstracts all of this behind a standard OpenAI-compatible API.
- **The client script is just an API caller.** It uses the `openai` Python package to send base64-encoded images to `http://127.0.0.1:8000/v1`. No torch, no transformers, no GPU imports. This keeps the client simple and testable.
- **Kill the server before CPU stages.** After OCR completes, shut down the vLLM server to free GPU memory. Diagnostics and rule-based cleanup are CPU-only and run in seconds.

### 3. SLURM Configuration

- **Partition selection on ALICE:**
  - `gpu-short`: A100 80GB, 4-hour limit. Best for fast turnaround. Request with `--gres=gpu:a100:1`.
  - `gpu_lucdh`: A40 48GB, 14-day limit. Best for long-running bulk jobs. Request with `--account=gpu_lucdh --partition=gpu_lucdh --gres=gpu:1`.
  - `gpu-a100-80g`: A100 80GB, 7-day limit. For sustained multi-day runs.
  - Check availability: `sinfo -p <partition> --format='%P %a %l %D %T %G'`
- **Resource requirements for Qwen3.5-35B-A3B-GPTQ-Int4:** 1 GPU (any A40/A100), 64GB RAM, 4 CPUs. The model uses ~21 GiB VRAM at 4-bit. An A40 (48GB) works; an A100 (80GB) gives more KV cache headroom.
- **Set offline mode.** Compute nodes cannot reach the internet. Set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` in the SLURM script. Without these, vLLM attempts to download model configs and fails silently.
- **Use `tee` for server logs.** Pipe vLLM server output to both stdout and a log file: `... 2>&1 | tee logs/vllm_server_${SLURM_JOB_ID}.log &`. Note that Python buffers stdout heavily in pipes — log output appears in bursts, not real-time.
- **Set the health check timeout to 900 seconds.** vLLM cold start on ALICE takes ~13 minutes due to ZFS I/O + Python imports + torch.compile + CUDA graph capture. The previous default of 600s was insufficient. Subsequent runs on the same node are faster due to cached compilation.

### 4. Cold Start Timeline

Observed on gpu-short A100 (April 2026):

| Phase | Duration | Notes |
|-------|----------|-------|
| Python imports | ~4 min | vLLM/torch cold import, CUDA extension loading |
| Config + engine init | ~2 min | Architecture resolution, attention backend selection |
| Weight loading (14 shards, 21 GiB) | ~2.5 min | ZFS network I/O |
| torch.compile (dynamo + inductor) | ~2.5 min | Bytecode transform + graph compilation |
| Profiling/warmup | ~1.5 min | Initial run with dummy data |
| CUDA graph capture (86 graphs) | ~10s | Fast once compilation is cached |
| **Total cold start** | **~13 min** | Health check sees /health after this |

- **Warm starts are much faster.** If the same model was recently loaded on the same node, OS page cache has the weight files and torch.compile cache is populated. Expect 3-5 minutes.
- **Log output is heavily buffered.** During the first 10+ minutes, the SLURM log file may show no new lines. This is Python's stdout buffering in the pipe, not a stalled process. Check GPU memory usage (`nvidia-smi --query-gpu=memory.used --format=csv,noheader`) via `srun --jobid=<id> --overlap` to verify the model is loading.

### 5. SSH Rules for ALICE

- **ControlMaster multiplexing is configured.** All `ssh alice3` calls share one gateway connection via `~/.ssh/control/`. This prevents gateway rate-limiting.
- **Do NOT poll rapidly.** Consolidate all checks into a single SSH call (chain with `;` or `&&`). Wait at least 2-3 minutes between checks when monitoring a running job. Rapid polling wastes the multiplex connection and can trigger rate limiting, locking you out for 5 minutes.
- **One check, everything you need.** Combine job status, log tail, and output listing:
  ```bash
  ssh alice3 "squeue -j <JOBID> -o '%.8T %.10M'; tail -10 logs/ocr_<JOBID>.out; ls ocr_output/ | head -10"
  ```
- **Track background SSH processes.** If using `run_in_background`, ensure all SSH commands complete. Kill any that hang before starting new work.
- **If locked out, wait 5 minutes.** The gateway rate limiter resets after 5 minutes of inactivity.

### 6. Troubleshooting

- **"ERROR: vLLM server not ready after Ns"**: Increase the timeout in `run_ocr.slurm`. Cold starts from ZFS take ~13 minutes. Set to 900s minimum.
- **GPU shows 0 MiB for several minutes**: Normal during Python import and weight loading phases. The process is in disk I/O (state `D`). Verify the process is alive: `ps -p <PID> -o state,rss,etime`.
- **Empty log file for 10+ minutes**: Python stdout buffering. The server is working. Check GPU memory instead.
- **"ModuleNotFoundError: No module named 'fitz'"**: Install PyMuPDF into the vLLM venv: `<venv>/bin/python -m pip install PyMuPDF`.
- **BitsAndBytes + MoE incompatibility**: Do not use BnB NF4 quantization with MoE models (Qwen3.5-35B-A3B). Use vLLM with `--quantization gptq_marlin` and GPTQ-Int4 pre-quantized weights instead.
- **Job completes but no OCR output**: Check if the vLLM server timed out before the client could connect. Increase health check timeout. Check `logs/vllm_server_<JOBID>.log` for server-side errors.

## Quality Checks

- [ ] **Model weights cached:** Verified model files exist at `$HF_HOME/hub/models--<model>/` on the cluster
- [ ] **vLLM venv verified:** Confirmed `vllm/__init__.py` exists in venv (NOT by importing)
- [ ] **Dependencies installed:** PyMuPDF and any other pipeline packages available in the vLLM venv
- [ ] **Code and data synced:** Pipeline scripts and source PDFs transferred to cluster storage
- [ ] **Manifest has cluster paths:** PDF paths point to `/zfsstore/` locations, not local paths
- [ ] **Offline mode set:** `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` exported in SLURM script
- [ ] **Health check timeout sufficient:** Set to 900s or higher for cold starts from ZFS
- [ ] **Logs directory exists:** `mkdir -p logs/` run before job submission
- [ ] **Output directory exists:** Target output directory created before job submission
- [ ] **Partition appropriate:** GPU partition chosen based on time limit needs and GPU availability
- [ ] **SSH discipline followed:** Checks consolidated into single calls, 2+ minutes between polls
