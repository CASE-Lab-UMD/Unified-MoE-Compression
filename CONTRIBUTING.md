# Contributing

Thanks for contributing to Unified-MoE-Compression.

## Development Setup

```bash
conda create -n moe-compression python=3.10 -y
conda activate moe-compression
pip install -e .
```

If your change touches quantization or benchmark paths, also install:

```bash
cd AutoAWQ && pip install -e . && cd AutoAWQ_kernels && pip install -e . && cd ../..
cd AutoGPTQ && pip install -vvv --no-build-isolation -e . && cd ..
cd lm-evaluation-harness && pip install -e . && cd ..
```

## Before Opening a PR

1. Inspect unresolved placeholders in scripts you plan to run (template placeholders are expected in this repository):

```bash
bash scripts/dev/check_placeholders.sh
```

2. Run at least one relevant script path for your change (for example pruning, finetuning, or evaluation) and include the command in the PR description.

3. Keep diffs focused. Avoid mixing unrelated refactors with functional changes.

## Coding Guidelines

- Follow existing project style in touched files.
- Keep shell scripts configurable through top-level variables.
- Prefer explicit paths and reproducible commands.
- Do not commit model checkpoints, dataset dumps, or generated result files.

## PR Description Checklist

Include the following in your PR:
- What changed and why.
- Which script(s) were tested.
- Hardware/runtime context when results matter (GPU type, number of GPUs, CUDA, torch version).
- Any behavior changes users should know before upgrading.
