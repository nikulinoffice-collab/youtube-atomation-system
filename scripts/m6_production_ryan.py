#!/usr/bin/env python3
"""M6.9 production Ryan synthesis bridge. Fail-closed; no publishing."""
from __future__ import annotations
import json, time, wave
from pathlib import Path
from scripts.m6_voice_script import normalize, validate
from scripts.m6_voice_plan import generate_voice_plan
from scripts.m6_voice_plan_validator import validate_voice_plan

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config/m6/qwen3_ryan_frozen.json"

class ProductionRyanError(RuntimeError): pass

def _write_wav(path, audio, sr):
    import numpy as np
    pcm=np.clip(np.asarray(audio,dtype=np.float32),-1.0,1.0)
    pcm16=(pcm*32767.0).astype("<i2")
    with wave.open(str(path),"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(sr)); w.writeframes(pcm16.tobytes())

def synthesize(text:str, output_path:Path)->dict:
    cfg=json.loads(CONFIG.read_text())
    if cfg.get("speaker")!="Ryan" or cfg.get("paid_services") is not False:
        raise ProductionRyanError("frozen Ryan/zero-cost invariant violated")
    normalized=normalize(text); validate(normalized)
    plan=generate_voice_plan(normalized); validate_voice_plan(plan,normalized)
    try:
        import torch
        from qwen_tts import Qwen3TTSModel
    except Exception as exc:
        raise ProductionRyanError(f"QWEN_RUNTIME_IMPORT_FAILED: {exc}") from exc
    model=Qwen3TTSModel.from_pretrained(cfg["model"],revision=cfg["model_revision"],device_map="cpu",dtype=torch.float32)
    started=time.perf_counter()
    wavs,sr=model.generate_custom_voice(text=plan["spoken_text"],language=cfg["language"],speaker=cfg["speaker"],
        instruct=cfg["instruction"],**cfg["generation"])
    elapsed=time.perf_counter()-started
    if not wavs: raise ProductionRyanError("QWEN_EMPTY_AUDIO")
    audio=wavs[0].detach().cpu().numpy() if hasattr(wavs[0],"detach") else wavs[0]
    output_path.parent.mkdir(parents=True,exist_ok=True); _write_wav(output_path,audio,sr)
    with wave.open(str(output_path),"rb") as w: duration=w.getnframes()/w.getframerate()
    return {"normalized":normalized,"voice_plan":plan,"sample_rate_hz":int(sr),"duration_s":duration,
            "synthesis_seconds":elapsed,"voice":"Ryan","model":cfg["model"],"model_revision":cfg["model_revision"]}
