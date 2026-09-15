# M6.0 Local TTS Dependency Audit

Status: IN_PROGRESS. Evidence captured 2026-09-15. This audit is for benchmark feasibility and licensing/compliance gating only; it does not certify a production engine.

## Chatterbox-Nano

Official `resemble-ai/chatterbox` packaging currently requires Python >=3.10 and declares numpy, librosa, s3tokenizer, torch/torchaudio, transformers, diffusers, `resemble-perth` from the upstream Perth Git repository, conformer, safetensors, spacy-pkuseg, pykakasi, gradio, pyloudnorm, and omegaconf. The package explicitly selects newer torch/torchaudio for Python 3.14. This is a materially heavier dependency stack than Kokoro and must be measured for cold-start/install time and RAM on the GitHub Actions runner.

Gate: benchmark only the official upstream stack. Preserve Perth provenance watermarking. Do not substitute forks intended to remove watermarking. Before commercial certification, record licenses for the direct dependencies that are actually redistributed by the Factory package and separately certify the selected reference voice recording.

## MOSS-TTS-Nano

Official `OpenMOSS/MOSS-TTS-Nano` requirements currently include numpy, FastAPI, python-multipart, sentencepiece, torch==2.7.0, torchaudio==2.7.0, transformers==4.57.1, uvicorn, WeTextProcessing, soundfile, and onnxruntime. Upstream setup documentation warns that WeTextProcessing/pynini may require special installation handling. The official workflow also loads a separate MOSS Audio Tokenizer model in addition to the TTS model.

Gate: use a clean supported Python environment for the benchmark and measure dependency-install time separately from model cold-start. Do not treat the 100M TTS parameter count as total runtime footprint because tokenizer/model dependencies are additional. Commercial certification still requires a Factory-owned or explicitly commercially licensed prompt/reference voice.

## Kokoro

Official `hexgrad/kokoro` package version 0.9.4 requires Python >=3.10,<3.14 and declares huggingface_hub, loguru, `misaki[en]>=0.9.4`, numpy, torch, and transformers. Therefore the current Python package is not compatible with Python 3.14 and the benchmark must pin a supported Python version rather than modifying production Python assumptions. English G2P is provided through the Misaki dependency chain; espeak-ng/GPL exposure must be recorded according to the exact installed path rather than assumed away.

Gate: benchmark the official package on a supported Python version. Record exact resolved dependency versions and licenses from the benchmark environment. If espeak-ng or another copyleft component is installed or bundled, treat this as a distribution/compliance obligation, not as a commercial-use prohibition. Voicepack provenance remains a separate unresolved rights gate.

## Benchmark environment rule

Local engines may require different supported Python versions. M6.0 must not force them into the production runtime merely to make one environment uniform. Benchmark jobs should use isolated environments and record: OS/runner, Python version, dependency install seconds, model download bytes/time where measurable, cold-start seconds, synthesis seconds, output duration, RTF, peak RAM where measurable, output artifact size, failures/retries, and GPU use.

No dependency result in this document authorizes production migration. M6.0 remains shadow-only and ends at HUMAN_REVIEW_REQUIRED after reproducible measurements and blind samples are complete.
