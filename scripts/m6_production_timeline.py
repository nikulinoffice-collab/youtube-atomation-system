#!/usr/bin/env python3
"""M6.9 bridge from canonical forced-alignment output to the legacy production timeline."""
from __future__ import annotations
import re
from typing import Sequence

LEXICAL_RE = re.compile(r"(?:[$€£]?[0-9]+(?:[.,][0-9]+)*(?:[KMB])?|[^\W_]+(?:['’][^\W_]+)*)", re.UNICODE | re.IGNORECASE)

class TimelineBridgeError(ValueError):
    pass

def _display_tokens(text: str):
    matches=list(LEXICAL_RE.finditer(text))
    out=[]; prefix=text[:matches[0].start()] if matches else ""
    for i,m in enumerate(matches):
        between=text[m.end():matches[i+1].start()] if i+1<len(matches) else text[m.end():]
        ws=re.search(r"\s",between)
        suffix=between[:ws.start()] if ws else between
        nxt=between[ws.start():] if ws else ""
        out.append({"separator_before":prefix,"word":m.group(0)+suffix})
        prefix=nxt
    return out

def build_production_timeline(display_text:str, word_timings:Sequence[dict], duration_s:float, *, voice="Ryan")->dict:
    tokens=_display_tokens(display_text)
    if not tokens or not word_timings:
        raise TimelineBridgeError("empty display text or alignment")
    # Forced alignment may expand one display token into several spoken words.
    # Group consecutive aligned words by canonical display_span_id.
    groups=[]
    for item in word_timings:
        did=str(item.get("display_span_id",""))
        if not did:
            raise TimelineBridgeError("alignment missing display_span_id")
        if groups and groups[-1]["id"]==did:
            groups[-1]["items"].append(item)
        else:
            groups.append({"id":did,"items":[item]})
    if len(groups)!=len(tokens):
        raise TimelineBridgeError(f"display/alignment coverage mismatch: {len(tokens)} tokens vs {len(groups)} groups")
    words=[]
    previous=0.0
    for index,(token,group) in enumerate(zip(tokens,groups)):
        start=float(group["items"][0]["start_s"]); end=float(group["items"][-1]["end_s"])
        if start < previous-1e-6 or end<=start or end>duration_s+0.02:
            raise TimelineBridgeError("non-monotonic or out-of-range alignment")
        words.append({"index":index,"separator_before":token["separator_before"],"word":token["word"],"start":round(start,4),"end":round(end,4)})
        previous=end
    reconstructed="".join(w["separator_before"]+w["word"] for w in words)
    if reconstructed!=display_text:
        raise TimelineBridgeError("canonical display text was not preserved")
    return {"schema_version":3,"source":"m6.9-qwen3-ryan-whisperx","text":display_text,"voice":voice,
            "duration":round(float(duration_s),4),"speech_start":words[0]["start"],"speech_end":words[-1]["end"],"words":words}
