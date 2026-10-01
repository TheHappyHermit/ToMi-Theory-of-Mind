---
name: local-inference-hosting
description: Use when deploying or tuning local LLM inference.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [llm, inference, llama.cpp, vllm, vulkan, rocm, gpu, vram, docker, benchmarking]
    related_skills: [local-inference-node, llama-cpp, serving-llms-vllm, docker-cleanup-and-vm-optimization]
---

# Local Inference Hosting

Deploying, placing, tuning, and measuring local LLM inference servers. One
skill for the whole class: the placement questions, the backend-specific
deployment facts, and the benchmarking discipline are one body of work, and
splitting them produced several near-identical skills in one install.

## When to Use

Deploying, pinning, tuning, or benchmarking local LLM inference — llama.cpp,
vLLM, or LM Studio on NVIDIA, AMD iGPU via Vulkan, or ROCm — including
multi-GPU placement, VRAM budgeting, and A/B benchmarking. Covers device
passthrough and quant-specific bugs.

## Step 1 — Enumerate the real hardware before theorising

Never reason about capacity from memory or from a description.

```bash
lspci -nn | grep -iE 'vga|display|3d'      # every accelerator present
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader
# map DRM card -> driver + PCI slot
for d in /sys/class/drm/card*/device; do
  [ -f "$d/uevent" ] && echo "$d -> $(grep -E 'DRIVER|PCI_SLOT_NAME' "$d/uevent" | tr '\n' ' ')"
done
```

### An iGPU may have DEDICATED VRAM — read the counters

An integrated GPU is **not** automatically "just system RAM":

```bash
for f in /sys/class/drm/card0/device/mem_info_vram_used \
         /sys/class/drm/card0/device/mem_info_vram_total \
         /sys/class/drm/card0/device/mem_info_gtt_used \
         /sys/class/drm/card0/device/mem_info_gtt_total; do
  [ -f "$f" ] && echo "$(basename "$f"): $(( $(cat "$f") / 1024 / 1024 )) MB"
done
```

- `mem_info_vram_*` = **dedicated** carve-out for that device.
- `mem_info_gtt_*` = a **separate** shared-system-RAM aperture.

Conflating them gives wrong advice in both directions — "no headroom" when
there is a large dedicated pool, or "32 GB free" when it is contended host
RAM. If you already told the user something based on the wrong pool, correct it
explicitly rather than quietly revising.

## Step 2 — Find what is actually running where

Config files say what should run; only the runtime's own logs say what does.
Confirm placement from the process log, then from the network side (which port
answers, with which model name in its banner). A model silently loaded on the
wrong device is the common failure, and a config-file reading will not catch
it.

## Step 3 — Enforce placement, then prove it

Pin with the runtime's device-selection flag (`CUDA_VISIBLE_DEVICES`,
`HIP_VISIBLE_DEVICES`, `--device`, or llama.cpp's device list), then verify
from the runtime's log that the intended device was chosen. Do not report
placement as done on the strength of the flag alone.

## Backend-specific facts worth keeping

### Docker device passthrough (any GPU backend in a container)

Both render nodes are required, and group membership must be **numeric**:

```yaml
services:
  chat:
    image: ghcr.io/ggml-org/llama.cpp:server-vulkan   # or your vLLM/ROCm image
    restart: unless-stopped
    shm_size: 1g
    devices:
      - "/dev/dri:/dev/dri"
      - "/dev/kfd:/dev/kfd"
    group_add:
      - "44"     # video  — VERIFY: getent group video
      - "992"    # render — VERIFY: getent group render
    ports:
      - "<HOST_PORT>:8080"
    volumes:
      - "<MODELS_DIR>:/models"
```

`shm_size` is not optional for large-context serving; the default container
shm will fail mid-load and look like an OOM.

### AMD iGPU via Vulkan

- iGPU-only models generally want `-ngl 99` (offload everything), and the
  counter-intuitive result is that **lowering `-ub` can help**, because a
  smaller ubatch reduces the staging-buffer high-water mark.
- **Q8_0 embedding models on Vulkan can return all-null or all-identical
  vectors.** The server looks healthy and serves garbage. When embeddings look
  degenerate, change the embedding model's quant before anything else.
- `--cache-reuse` behaves badly at long context on iGPU; verify output
  determinism before enabling it in production.

### ROCm

Check the kernel/driver matrix before blaming the model: an ROCm image on an
unsupported kernel will fall back or refuse to init. Whisper.cpp STT and
Kokoro TTS on the same device compete for VRAM — budget for both resident.

## Step 4 — Budget VRAM empirically

Do not extrapolate from a paper's per-layer numbers. Load the actual model,
measure, and record: model, quant, context, batch, ubatch, threads, and
measured peak. Two resident models (chat + embed) on one iGPU is the common
case where the budget is genuinely tight.

## Benchmarking discipline

- **A/B one variable at a time.** Change the quant, or the context, or the
  batch — not three. A result that moves three knobs is unattributable.
- **Separate decode from prefill.** They scale differently; a config that
  improves one can regress the other.
- **Warm up before measuring.** First-run timings include load and page-in.
- **Report the harness, not just the number**: model, quant, context, batch,
  ubatch, threads, backend, and whether it is decode, prefill, or TTFT.
- Do not compare a number from a different harness to one from this skill and
  call the difference a finding.

## Shared-host etiquette

On a host with other people or other agents: one workload per device by
default, announce long jobs, and do not silently reclaim VRAM another process
is using. Check what is resident before starting a model that wants most of
the card.

## Pitfalls

- Reasoning about VRAM from a spec sheet, or from the wrong pool.
- Treating a config file as proof of placement.
- Trusting a healthy-looking server that returns degenerate embeddings.
- Benchmarking with the model still loading, or with three knobs changed.
- Omitting `shm_size` and diagnosing the resulting failure as OOM.
- Hardcoding a GID that differs on the target host — resolve it there.
- Reporting a benchmark without the harness, making it unfalsifiable.

## Reporting results

State the hardware you found (with the pools you actually read), what you
placed where and how you verified it, the VRAM budget with measured numbers,
and the benchmark with its full harness. Include what you could not verify.
