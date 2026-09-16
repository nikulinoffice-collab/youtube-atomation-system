# M6.0 Local TTS Dependency Audit

Status: IN_PROGRESS. Evidence captured 2026-09-15 through 2026-09-16. This audit is for benchmark feasibility and licensing/compliance gating only; it does not certify a production engine.

## Chatterbox-Nano

Official `resemble-ai/chatterbox` packaging currently requires Python >=3.10 and declares numpy, librosa, s3tokenizer, torch/torchaudio, transformers, diffusers, `resemble-perth` from the upstream Perth Git repository, conformer, safetensors, spacy-pkuseg, pykakasi, gradio, pyloudnorm, and omegaconf. The package explicitly selects newer torch/torchaudio for Python 3.14. This is a materially heavier dependency stack than Kokoro and must be measured for cold-start/install time and RAM on the GitHub Actions runner.

Gate: benchmark only the official upstream stack. Preserve Perth provenance watermarking. Do not substitute forks intended to remove watermarking. Before commercial certification, record licenses for the direct dependencies that are actually redistributed by the Factory package and separately certify the selected reference voice recording.

## MOSS-TTS-Nano

Official `OpenMOSS/MOSS-TTS-Nano` requirements currently include numpy, FastAPI, python-multipart, sentencepiece, torch==2.7.0, torchaudio==2.7.0, transformers==4.57.1, uvicorn, WeTextProcessing, soundfile, and onnxruntime. Upstream setup documentation warns that WeTextProcessing/pynini may require special installation handling. The official workflow also loads a separate MOSS Audio Tokenizer model in addition to the TTS model.

### Measured GitHub Actions CPU evidence — 2026-09-16

Exact validation evidence: workflow run `35066198346`, job `104696923890`, source SHA `3670919d3f74d456d792d2aa80885f46da909bf3`. Runner was Ubuntu 24.04.5 (`ubuntu-24.04` image `20260907.300.1`), Python 3.12.14, 4 CPU, 15,989 MiB RAM. The benchmark pinned upstream MOSS commit `8b7bcc9341b3b4ef3a3a58ba1338a7d85ff133eb`, CPU-only `torch==2.7.0+cpu` / `torchaudio==2.7.0+cpu`, ONNX Runtime 1.30.0, `pynini==2.1.6.post1`, and WeTextProcessing commit `bb145729c903fac2d9fddf6b9077f352f3fc2816`. `pip check` passed; `torch.cuda.is_available()` was false; ONNX Runtime exposed `CPUExecutionProvider`; the validation explicitly rejected installed NVIDIA/CUDA runtime packages. Dependency installation took 36 s in this run.

The cold synthesis used the exact text `Is AI really going to destroy us? The answer is more complicated than the headlines suggest.` with upstream `assets/audio/en_2.wav`. First execution downloaded approximately 728 MiB of ONNX model assets and built WeText normalization FSTs. Cold wall time was 93.90 s, cold peak RSS 8,167,700 KiB (~7.79 GiB), and output was 7.52 s, 48 kHz stereo. Cold timing therefore includes model download and one-time text-normalization construction and must not be treated as steady-state RTF.

Three subsequent measured executions reused the downloaded models and existing WeText FST cache. Results were: run 1 = 20.3137 s / 7.52 s audio / RTF 2.7013 / peak RSS 2,575,732 KiB; run 2 = 21.2777 s / RTF 2.8295 / peak RSS 2,575,176 KiB; run 3 = 22.4362 s / RTF 2.9835 / peak RSS 2,574,824 KiB. Mean elapsed = 21.3425 s and mean RTF = 2.8381. Each WAV was 1,443,884 bytes, 48 kHz stereo. Failures/retries = 0; GPU use = false.

Interpretation: the measured cached CLI path is materially slower than realtime on this GitHub-hosted 4-CPU runner (mean RTF 2.84). These measurements are reproducible runtime evidence for the tested pinned stack, not a universal claim about newer upstream MOSS releases or an in-process server that retains inference sessions. Current upstream documentation now advertises a newer fully standalone PyTorch-free ONNX CPU path and nearly 2x efficiency relative to the original path; that later upstream state is separate from this pinned benchmark and must not retroactively change these measurements.

Licensing status remains `TECHNICAL_ONLY / NOT_COMMERCIAL_CERTIFIED`. The benchmark intentionally used the upstream bundled reference recording `assets/audio/en_2.wav`; Apache-2.0 model/code licensing does not independently establish the recording/personality rights needed for Factory commercial output. Production certification requires a Factory-owned or explicitly commercially licensed reference voice, plus the remaining dependency/output-rights audit.

Gate: use a clean supported Python environment for the benchmark and measure dependency-install time separately from model cold-start. Do not treat the 100M TTS parameter count as total runtime footprint because tokenizer/model dependencies are additional. Commercial certification still requires a Factory-owned or explicitly commercially licensed prompt/reference voice.

## Kokoro

Official `hexgrad/kokoro` package version 0.9.4 requires Python >=3.10,<3.14 and declares huggingface_hub, loguru, `misaki[en]>=0.9.4`, numpy, torch, and transformers. Therefore the current Python package is not compatible with Python 3.14 and the benchmark must pin a supported Python version rather than modifying production Python assumptions. English G2P is provided through the Misaki dependency chain; espeak-ng/GPL exposure must be recorded according to the exact installed path rather than assumed away.

### Measured GitHub Actions CPU evidence — 2026-09-16

Exact validation evidence: workflow run `35099435301`, job `104804817492`, source SHA `c3f1191d70a0235cb011e686e8c194813335950c`. Runner was Ubuntu 24.04.5 (`ubuntu-24.04` image `20260907.300.1`), Python 3.11.16, 4 CPU, 15,989 MiB RAM. The isolated job installed `kokoro==0.9.4`, soundfile and psutil plus system espeak-ng/FFmpeg; `pip check` passed. The resolver selected `torch==2.14.0+cu130`, but the runner had no CUDA device and `torch.cuda.is_available()` was false. This is CPU execution evidence, not a CPU-only dependency-footprint result: the default PyPI Torch resolution downloaded a large CUDA 13 runtime stack and is therefore operationally inefficient for GitHub-hosted CPU runners. Dependency/system installation took 120 s.

The benchmark used frozen corpus case `hook`, exact text `AI is changing everything — faster than most people realize.`, SHA-256 `abf21554cb44c7540135d10495e7dd7abdee8d6dc725c06a142f81ccbfaa42bf`, voice `af_heart`, speed 1, and a single `KPipeline(lang_code='a')` process for all three runs. Pipeline initialization was 4.6372 s. Run 1 = 2.7631 s synthesis / 4.25 s audio / RTF 0.6501 / process RSS 1,642,270,720 bytes. Run 2 = 2.0702 s / RTF 0.4871 / RSS 1,701,380,096 bytes. Run 3 = 2.0147 s / RTF 0.4740 / RSS 1,714,786,304 bytes. Mean synthesis time = 2.2827 s and mean RTF = 0.5371. Each output was 204,044 bytes, 24 kHz WAV. Whole benchmark-process maximum RSS from `/usr/bin/time -v` was 1,742,520 KiB (~1.66 GiB). Hugging Face cache after the run was 313 MiB. Failures/retries = 0; GPU availability/use = false. Artifact `m6-kokoro-cpu-technical-only`, ID `10447083576`, contained the three WAVs and results JSON; uploaded ZIP size was 433,332 bytes with SHA-256 `b5695df4ae7127b9c3e9779a6f22aeadf571e1b0e1f42c5af6e2ad3bca52807b`.

Interpretation: on this runner Kokoro produced the tested 4.25 s corpus hook faster than realtime after initialization, with warm RTF approaching 0.47–0.49. However, the default package install is unnecessarily heavy for a CPU-only Actions environment because PyPI Torch pulled CUDA libraries. A later integration benchmark should use an explicitly CPU-only compatible Torch resolution if the official package remains compatible; the present synthesis measurements remain valid for the exact tested environment.

Licensing/compliance status remains `TECHNICAL_ONLY / NOT_COMMERCIAL_CERTIFIED_PENDING_EXPLICIT_VOICEPACK_RIGHTS`. Upstream model materials identify Kokoro-82M weights as Apache-2.0 and describe production deployment, but M6 keeps the selected `af_heart` voicepack as a separate rights gate until explicit authoritative voicepack rights are recorded. The exact installed English G2P path also included `espeakng-loader`, `phonemizer-fork`, system espeak-ng and `num2words`; their copyleft/LGPL obligations must be handled as distribution/compliance obligations rather than incorrectly treated as a ban on commercial inference.

Gate: benchmark the official package on a supported Python version. Record exact resolved dependency versions and licenses from the benchmark environment. If espeak-ng or another copyleft component is installed or bundled, treat this as a distribution/compliance obligation, not as a commercial-use prohibition. Voicepack provenance remains a separate unresolved rights gate.

## Benchmark environment rule

Local engines may require different supported Python versions. M6.0 must not force them into the production runtime merely to make one environment uniform. Benchmark jobs should use isolated environments and record: OS/runner, Python version, dependency install seconds, model download bytes/time where measurable, cold-start seconds, synthesis seconds, output duration, RTF, peak RAM where measurable, output artifact size, failures/retries, and GPU use.

No dependency result in this document authorizes production migration. M6.0 remains shadow-only and ends at HUMAN_REVIEW_REQUIRED after reproducible measurements and blind samples are complete.
