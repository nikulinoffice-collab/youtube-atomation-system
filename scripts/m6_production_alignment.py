#!/usr/bin/env python3
"""M6.9 real WhisperX alignment bridge for the production Ryan path."""
from __future__ import annotations
import re
from pathlib import Path

class ProductionAlignmentError(RuntimeError): pass

def _norm(s:str)->str:
    return re.sub(r"[^a-z0-9']+","",s.casefold())

def align(wav_path:Path, voice_plan:dict, *, device="cpu")->dict:
    try:
        import whisperx
    except Exception as exc:
        raise ProductionAlignmentError(f"WHISPERX_IMPORT_FAILED: {exc}") from exc
    audio=whisperx.load_audio(str(wav_path))
    model=whisperx.load_model("tiny.en",device,compute_type="int8")
    raw=model.transcribe(audio,batch_size=4,language="en")
    align_model, metadata=whisperx.load_align_model(language_code="en",device=device)
    result=whisperx.align(raw["segments"],align_model,metadata,audio,device,return_char_alignments=False)
    observed=[]
    for seg in result.get("segments",[]):
        observed.extend(seg.get("words",[]))
    observed=[w for w in observed if w.get("start") is not None and w.get("end") is not None and _norm(str(w.get("word","")))]
    expected=[]
    for block in voice_plan["blocks"]:
        text=voice_plan["spoken_text"][block["spoken_span"]["start"]:block["spoken_span"]["end"]]
        for token in text.split():
            expected.append((block,token))
    if len(observed)!=len(expected):
        raise ProductionAlignmentError(f"WHISPERX_COVERAGE_MISMATCH: expected={len(expected)} observed={len(observed)}")
    timings=[]
    per_block={}
    for (block,token),obs in zip(expected,observed):
        if _norm(token)!=_norm(str(obs["word"])):
            raise ProductionAlignmentError(f"WHISPERX_TOKEN_MISMATCH: expected={token!r} observed={obs['word']!r}")
        bid=block["block_id"]; idx=per_block.get(bid,0); per_block[bid]=idx+1
        # Production timeline bridge groups by display span identity. The VoicePlan
        # block display span is canonical and survives spoken expansions.
        did=f"display:{block['display_span']['start']}:{block['display_span']['end']}"
        timings.append({"block_id":bid,"spoken_span_id":f"spoken:{block['spoken_span']['start']}:{block['spoken_span']['end']}",
          "display_span_id":did,"token_index":idx,"spoken_text":token,"display_text":voice_plan["display_text"][block["display_span"]["start"]:block["display_span"]["end"]],
          "start_s":float(obs["start"]),"end_s":float(obs["end"]),"confidence":float(obs.get("score",1.0))})
    return {"version":"m6.9-whisperx-production-v1","word_timings":timings,"coverage":{"expected_words":len(expected),"aligned_words":len(timings)}}
