# M6.0 Blind Listening Package Evidence

Status: PASS / HUMAN_REVIEW_REQUIRED_M6_0

The blind listening package was assembled from the already completed, cryptographically bound Edge legacy, Kokoro and Chatterbox-Nano frozen-corpus artifacts. No new speech synthesis occurred in this packaging run.

## Actions binding

- Branch: `factory-v1-voice-m6`
- Package commit: `a1daaf392a2698f18135d283ffed506e405108f8`
- Run: `35466434371`
- Job: `105959502286`
- Conclusion: `success`
- Validation: `BLIND_PACKAGE=PASS samples=36`
- Matrix: 12 frozen cases x 3 engines = 36 samples
- Reviewer manifest SHA-256: `1b14071ba98912b37776d6436b45c607549782089ff4cfafbdd8cfade683960b`
- Audit binding manifest SHA-256: `6a2257412d10495f3eaa33406c1ef7d484767a91642303bc0b8619185ce9e4fb`

## Reviewer artifact

- Artifact ID: `10591332016`
- Name: `m6-blind-review-a1daaf392a2698f18135d283ffed506e405108f8`
- ZIP size: 9,448,856 bytes
- ZIP SHA-256: `be80bfe467671469a5c9df301405cfdf23741b448f36c7da0af69dcb9b3b4785`
- Contains 36 engine-neutral WAV samples plus reviewer manifest/readme.
- Reviewer-facing manifest does not expose `engine_id`.

## Sealed audit artifact

- Artifact ID: `10591257107`
- Name: `m6-blind-audit-map-a1daaf392a2698f18135d283ffed506e405108f8`
- ZIP size: 3,112 bytes
- ZIP SHA-256: `feffa2a13af929a696fab05c2623f01ff6af10b4ca0f708574379fb02957c365`
- Maps opaque sample IDs to engine identity/version/config and cryptographic source/audio bindings.
- This mapping should remain unopened by the reviewer until blind scoring is complete.

## Gate

M6.0 is now at `HUMAN_REVIEW_REQUIRED_M6_0` for the three-engine technical listening set. Kokoro and Chatterbox-Nano remain evaluation-only because their selected voice/reference asset rights are not commercially certified. MOSS remains fail-closed pending tested reference-audio rights. Gemini runtime remains blocked by free-tier credential/billing attestation. No engine is selected here.

Production voice behavior changed: NO. M5/main changed: NO. Paid services/billing/secrets/publishing: NO.
