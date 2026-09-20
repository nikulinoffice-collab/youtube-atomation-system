# M6 Qwen3-TTS runtime probe evidence

Run: 35500905857
Job: 106052375732
Exact repository SHA: 1ccfc4587a3976ea0f483aa946bc56134172270f
Conclusion: PASS

Environment: Ubuntu 24.04.5, Python 3.11.16, x86_64, 4 CPU, about 16 GiB RAM.

Runtime:
- official QwenLM/Qwen3-TTS source resolved at upstream commit 022e286b98fbec7e1e916cb940cdf532cd9f488e
- qwen-tts 0.1.1
- torch 2.14.0+cpu
- torchaudio 2.11.0+cpu
- CUDA false; no NVIDIA/CUDA runtime packages detected
- pip check PASS
- runtime import PASS
- flash-attn absent; manual PyTorch path used
- SoX executable warning observed; it did not invalidate this import/metadata probe. A synthesis workflow must install system SoX explicitly if the runtime path needs it.

Official checkpoint metadata resolved:
- Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice @ 85e237c12c027371202489a0ec509ded67b5e4b5 — apache-2.0
- Qwen/Qwen3-TTS-12Hz-0.6B-Base @ 5d83992436eae1d760afd27aff78a71d676296fc — apache-2.0
- Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice @ 0c0e3051f131929182e2c023b9537f8b1c68adfe — apache-2.0

Artifact: 10601837816
Artifact ZIP SHA256: 39ac42244f2a8d97a22052a3adbbd15f1ff76200f4937ff269b8bfa4be2dab35

No synthesis or reference voice was used in this gate. No paid API, billing, secret, publishing or production voice change occurred.

Next gate: a bounded male-only CustomVoice synthesis probe using official built-in English male speakers (Ryan and Aiden), with no voice cloning/reference recording. Their model availability is documented upstream; this technical use does not by itself certify independent personality/voice-asset rights for production.
