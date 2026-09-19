# M6.0 Chatterbox-Nano Full Frozen-Corpus Runtime Evidence

Status: PASS (technical benchmark only)

This record preserves durable runtime evidence for the shadow-only Chatterbox-Nano full frozen-corpus benchmark. It does not certify Chatterbox-Nano for commercial production and does not select an M6 engine.

## Repository and Actions binding

- Branch: `factory-v1-voice-m6`
- Benchmark commit: `a991c36ec29689d551aa9a647b2ed16aaa43457a`
- Workflow: `M6 Chatterbox Nano Full Corpus One Shot`
- Actions run: `35463887964`
- Job: `105952477622`
- Conclusion: `success`
- Upstream commit: `5de7a54aa4e5e2baadb0182dde554908b48b85c2`
- API: `chatterbox.tts_turbo.ChatterboxTurboTTS.from_pretrained(device="cpu", nano=True)`
- Nano identity gate: PASS
- Model class: `ChatterboxTurboTTS`
- Runtime: Ubuntu 24.04, Python 3.11
- Execution: CPU-only; CUDA unavailable
- Sample rate: 24 kHz
- Initialization: 23.384803 s

## Frozen corpus result

Manifest verification passed with `verified_cases=12`. All 12 cases synthesized and `BOUND_RECORDS=PASS count=12`.

| Case | Synth s | Audio s | RTF | State | Audio SHA-256 |
| --- | ---: | ---: | ---: | --- | --- |
| hook | 11.773047 | 3.880 | 3.034291 | cold | `0c82f75f467d52ae952e3f99f2328bba3c63dc21ba85b1da8451f07edd83bbf3` |
| question | 3.543674 | 3.160 | 1.121416 | warm | `a19ff5e8c2b2cdb490f96589950c873e27936df90a7352dd9a3599b117c8c00c` |
| contrast | 3.453808 | 3.120 | 1.106990 | warm | `25de93dce7d90d6da0a63b0b1e6ce3c30e0dfd361b22386ecd68b30c50d9a4cd` |
| important_fact | 3.545076 | 3.240 | 1.094159 | warm | `364a8e730b7a7bc558326167b92681da4de23ddf5597546a5f90f17bf45c0875` |
| reveal | 2.945145 | 2.400 | 1.227144 | warm | `439b0bfb3aa65b2dceff0a5539fdb83de9a510143199471193ed1ba0e5e6d28d` |
| neutral | 4.289483 | 4.240 | 1.011671 | warm | `d9ddaebfd5eaa9e45b867125cc59367fa643d6bbd50c9303966a37462e2a05ae` |
| numbers_dates | 6.586676 | 7.280 | 0.904763 | warm | `4d0261c46894d4653b021a402b3100017de25a5d51505e3b24d59ab072ca8590` |
| acronyms | 5.108078 | 4.840 | 1.055388 | warm | `20ab1376ceaa6c49c2374c2335185dc04c413feda5865eb9122d226da0677df0` |
| versions_units | 4.853108 | 4.920 | 0.986404 | warm | `e9926b9dc6385b849631362403a8e8061713a256770a0895f6a4218bb71a49af` |
| long_sentence | 10.226249 | 11.520 | 0.887695 | warm | `35f54da4150ef17a09805ad1d0422e2eae8edc2cd6fc89243804af404d818cf9` |
| paragraphs | 9.069063 | 9.880 | 0.917921 | warm | `40e4a2584dc26c27a7f836b36264826e68fedc4c3c8a24eef384b4dbf4e2cdac` |
| short_30s | 18.116903 | 20.760 | 0.872683 | warm | `d92c59e5bf476825968da649531d563fb3738f463a3ea3f8d71ac4a6fcd03396` |

## Artifact

- Artifact ID: `10590806967`
- Name: `m6-chatterbox-nano-full-corpus-a991c36ec29689d551aa9a647b2ed16aaa43457a`
- Files: 26
- Size: 3,065,561 bytes
- SHA-256: `5416614fcc7b6068725d9924ca5f9cf059a4a44dd03ebe7c5d6d886de99467a5`
- Retention: 7 days

## Qualification limits

This establishes reproducible CPU runtime feasibility for the exact Nano path. It is not a commercial-rights certification. Code/model licensing and rights to any built-in/reference voice asset are separate gates. Current status remains `TECHNICAL_ONLY / NOT_COMMERCIAL_CERTIFIED_PENDING_BUILTIN_REFERENCE_VOICE_RIGHTS` until the voice/reference/model-card asset rights and generated-output restrictions are independently closed.

Production voice behavior changed: NO. M5/main changed: NO. Paid API/billing/publishing/secrets: NO.
