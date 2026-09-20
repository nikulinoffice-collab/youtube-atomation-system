# M6.0 2026 Candidate License / Rights Audit

Status: COMPLETE_FOR_TECHNICAL_PROBE_SELECTION
Date: 2026-09-20

Purpose: screen Qwen3-TTS, IndexTTS-2.5 and CosyVoice3 against the Factory four-part gate before spending Actions compute. This audit does not grant rights to a user-supplied or demo voice recording.

## Qwen3-TTS

1. Code/repository: PASS. Official QwenLM/Qwen3-TTS repository carries Apache-2.0.
2. Model/checkpoint: PASS FOR TECHNICAL PROBE. Official Qwen3-TTS model materials identify Apache-2.0 licensing.
3. Voice/reference asset: CONDITIONAL. Voice-cloning paths accept a reference recording; rights to that recording remain independent. The probe must not use a celebrity/public-figure voice or an unverified demo voice. A production-qualified clone requires a Factory-owned or explicitly commercially licensed adult male reference.
4. Commercial generated-output restriction: no model-license prohibition identified in the inspected Apache-2.0 official materials; reference/personality rights remain separately gated.

Disposition: FIRST TECHNICAL PROBE. Prefer an official CustomVoice male preset only if its exact asset/use terms are explicit; otherwise test model runtime without claiming voice-rights certification.

## IndexTTS-2.5

1. Code/model grant: CUSTOM LICENSE. The official model uses the bilibili Model Use License Agreement rather than a standard permissive OSI license.
2. Model/checkpoint: CONDITIONAL. The license grants a worldwide, non-exclusive, non-transferable, free license subject to its restrictions.
3. Voice/reference asset: CONDITIONAL. Zero-shot cloning still requires independently controlled/licensed reference audio.
4. Commercial/output constraints: RESTRICTED/REQUIRES LEGAL REVIEW. The agreement defines model outputs/derivatives broadly and imposes downstream/compliance restrictions, including restrictions on using the model/derivatives to improve other AI models.

Disposition: HOLD_BEFORE_RUNTIME for this zero-cost production pipeline. Do not spend Actions compute until the custom license is affirmatively accepted as compatible with the intended commercial distribution/use.

## CosyVoice3 / Fun-CosyVoice3-0.5B

1. Code/repository: official project code must be pinned and audited at the exact upstream revision before runtime.
2. Model/checkpoint: Apache-2.0 evidence exists for Fun-CosyVoice3-0.5B-2512 model artifacts in published model metadata; exact official checkpoint provenance must be pinned in the runtime job.
3. Voice/reference asset: CONDITIONAL. Zero-shot/instruct paths can depend on prompt/reference audio; that recording's rights remain independent.
4. Commercial generated-output restriction: no Apache-2.0 model prohibition identified for the model artifact, but exact reference voice and dependency/distribution obligations remain gated.

Disposition: SECOND TECHNICAL PROBE after Qwen3-TTS, provided the job pins the official checkpoint and uses no unverified reference/personality asset.

## Selection

Qwen3-TTS is selected for the next technical runtime feasibility probe because its official code/model licensing path is the clearest of these three and it directly supports modern voice-cloning/custom-voice workflows relevant to the robotic-voice failure. This is not a quality winner and not a production selection.

IndexTTS-2.5 is held fail-closed on its custom license. CosyVoice3 remains eligible as the next comparison after Qwen3-TTS.

Production voice unchanged. No paid service, billing, publishing, secret, or production migration is authorized.
