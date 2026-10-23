# AI News Shorts — Manual Draft Pipeline (PRE-M7)

This repository generates **nonpublishing** AI/technology news Shorts drafts. The active `factory-v1-voice-m6` branch is under PRE-M7 qualification. Video publishing and uploading are **disabled** in the production route; there is no automatic three-times-daily publishing schedule.

## Current production chain

1. Retrieve a real AI/technology news topic from RSS and generate a sourced script using Gemini.
2. Generate narration with the committed M6.9 **Ryan/Qwen3** route, then align speech using WhisperX and produce the canonical narration timeline. Edge TTS is an explicit rollback route, not the default production voice.
3. Generate the storyboard, retrieve and rank source/stock visuals, and preserve mandatory Source Cards and controlled still-motion.
4. Build captions from the canonical timeline, render the 1080 × 1920 / 30 fps MP4, and run technical/visual QC.
5. Produce a **draft package only**. No YouTube upload, Google Sheets posting, OAuth publishing, or social-media publication is invoked.

Critical artifacts are bound to the active run and verified using producer/schema identity, payload hashes, and exact upstream media hashes. Missing or mismatched inputs fail closed.

## GitHub Actions

- `.github/workflows/publish.yml` — manually dispatched **Generate Draft Short**; `contents: read`; no upload agent, publishing, or automatic cron.
- `.github/workflows/m6-qualification.yml` — exact-SHA M6 regression and PRE-M7 contract qualification. A green run does **not** by itself prove the complete real clean-room E2E chain.
- `.github/workflows/m6-9-production-canary.yml` — historical/temporary Ryan fixture canary, **not** a full production E2E qualification. Retained until evidence/reference cleanup can safely remove it.

The draft workflow uses the existing `GEMINI_API_KEY` and `PEXELS_API_KEY` secrets and free-tier APIs. Topic history is persisted through Actions cache; after a cache miss the manual `bootstrap_topic_history` input must be explicitly enabled. Do not enable publishing, introduce new secrets or billing, or bypass the default-deny uploader authorization gate.

## Reproducibility and safety

Production Python dependencies are installed through `requirements.txt` and the shared exact constraints file `constraints/m6-qualification.txt`. Both qualification and draft workflows use the same lock, and `pip check` and regression tests enforce the dependency contract. The validated `qwen-tts==0.1.1` and `whisperx==3.8.6` identities remain frozen.

`factory-v1-storyboard` is a frozen reference branch and must never be modified by PRE-M7 work. Ryan/Qwen voice identity and quality parameters, existing QC gates, and explicit authorization boundaries must remain unchanged. For current audit evidence, Gate status, and exact qualification SHAs, consult `docs/audit/PRE_M7_FULL_REPOSITORY_AUDIT.md`.

## Local development

```bash
python -m pip install -r requirements.txt -c constraints/m6-qualification.txt
python -m pip check
python -m playwright install chromium
python -m pytest -q tests/
```

Local draft generation also requires the existing configured API access and runtime prerequisites. Never invoke `agents/upload_agent.py` as part of audit, qualification, or draft generation.

---

<h2 align="center">👋 Author</h2>

<p align="center">
  <b>Hasindu Udara</b><br>
  Software Engineering student · Full-stack developer
</p>

<p align="center">
  <a href="https://www.linkedin.com/in/hasindu-udara">
    <img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn">
  </a>
  <a href="https://hasinduudara.me/#home">
    <img src="https://img.shields.io/badge/Portfolio-111827?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Portfolio">
  </a>
  <a href="mailto:hasiduudara@gmail.com">
    <img src="https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white" alt="Email">
  </a>
</p>