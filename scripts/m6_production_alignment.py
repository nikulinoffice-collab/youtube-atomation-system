#!/usr/bin/env python3
"""M6.9 real WhisperX alignment bridge for the production Ryan path.

WhisperX word observations are not required to have the same token boundaries as
canonical spoken text.  This bridge binds them by normalized lexical content and
then projects timings back to canonical spoken/display tokens.  Coverage remains
fail-closed: the complete ordered normalized stream must match exactly.
"""
from __future__ import annotations
import re
from pathlib import Path

class ProductionAlignmentError(RuntimeError): pass

def _norm(s:str)->str:
    return re.sub(r"[^a-z0-9']+","",s.casefold())

def _lexical_spans(text:str):
    return [(m.start(),m.end(),m.group(0)) for m in re.finditer(r"(?:[$€£]?[0-9]+(?:[.,][0-9]+)*(?:[KMB])?|[^\W_]+(?:['’][^\W_]+)*)",text,re.UNICODE|re.IGNORECASE)]

def _spoken_to_display(normalized:dict,pos:int,*,end:bool=False)->int:
    dtext=normalized["display_text"]; mappings=normalized.get("mappings",[]); dcur=scur=0
    for m in mappings:
        unchanged=m["spoken_start"]-scur
        if pos<=scur+unchanged: return min(len(dtext),dcur+(pos-scur))
        dcur+=unchanged; scur+=unchanged
        if pos<=m["spoken_end"]:
            return m["display_end"] if end or pos==m["spoken_end"] else m["display_start"]
        dcur=m["display_end"]; scur=m["spoken_end"]
    return min(len(dtext),dcur+(pos-scur))

def _bind_tokens(canonical:list[dict], observed:list[dict])->list[dict]:
    """Map arbitrary aligner token boundaries onto canonical tokens exactly.

    A group may contain N canonical and M observed tokens.  The smallest prefixes
    whose concatenated normalized lexical streams match are bound together.  Each
    canonical token receives a monotonic proportional sub-range of the observed
    group's real time range; no text is invented or dropped.
    """
    out=[]; ci=oi=0
    while ci<len(canonical) and oi<len(observed):
        c0=ci; o0=oi; cs=os=""
        while True:
            if cs==os and cs: break
            if (len(cs)<=len(os) and ci<len(canonical)) or oi>=len(observed):
                cs+=_norm(canonical[ci]["text"]); ci+=1
            elif oi<len(observed):
                os+=_norm(str(observed[oi]["word"])); oi+=1
            else: break
            if cs and os and not (cs.startswith(os) or os.startswith(cs)):
                raise ProductionAlignmentError(f"WHISPERX_TOKEN_MISMATCH: canonical={cs!r} observed={os!r}")
        if not cs or cs!=os:
            raise ProductionAlignmentError(f"WHISPERX_COVERAGE_MISMATCH: canonical={cs!r} observed={os!r}")
        obs_group=observed[o0:oi]; can_group=canonical[c0:ci]
        start=float(obs_group[0]["start"]); end=float(obs_group[-1]["end"])
        total=sum(max(1,len(_norm(x["text"]))) for x in can_group); cursor=start
        min_score=min(float(x.get("score",1.0)) for x in obs_group)
        used=0
        for k,item in enumerate(can_group):
            used+=max(1,len(_norm(item["text"])))
            token_end=end if k==len(can_group)-1 else start+(end-start)*(used/total)
            out.append({**item,"start_s":cursor,"end_s":token_end,"confidence":min_score})
            cursor=token_end
    if ci!=len(canonical) or oi!=len(observed):
        raise ProductionAlignmentError(f"WHISPERX_COVERAGE_MISMATCH: canonical_remaining={len(canonical)-ci} observed_remaining={len(observed)-oi}")
    return out

def _canonical_tokens(voice_plan:dict,normalized:dict)->list[dict]:
    display_spans=_lexical_spans(voice_plan["display_text"]); result=[]
    for block in voice_plan["blocks"]:
        s0=block["spoken_span"]["start"]; s1=block["spoken_span"]["end"]
        per_block=0
        for a,b,text in _lexical_spans(voice_plan["spoken_text"][s0:s1]):
            sa=s0+a; sb=s0+b; da=_spoken_to_display(normalized,sa); db=_spoken_to_display(normalized,sb,end=True)
            candidates=[(i,x) for i,x in enumerate(display_spans) if x[0]<max(db,da+1) and x[1]>da]
            if not candidates:
                raise ProductionAlignmentError(f"DISPLAY_MAPPING_MISSING: spoken={text!r} span={sa}:{sb}")
            di,dspan=candidates[0]
            result.append({"block_id":block["block_id"],"spoken_span_id":f"spoken:{block['spoken_span']['start']}:{block['spoken_span']['end']}",
                "display_span_id":f"display-token:{di}:{dspan[0]}:{dspan[1]}","token_index":per_block,
                "spoken_text":text,"display_text":voice_plan["display_text"][dspan[0]:dspan[1]],"text":text})
            per_block+=1
    return result

def align(wav_path:Path, voice_plan:dict, normalized:dict, *, device="cpu")->dict:
    try: import whisperx
    except Exception as exc: raise ProductionAlignmentError(f"WHISPERX_IMPORT_FAILED: {exc}") from exc
    audio=whisperx.load_audio(str(wav_path)); model=whisperx.load_model("tiny.en",device,compute_type="int8")
    raw=model.transcribe(audio,batch_size=4,language="en")
    align_model,metadata=whisperx.load_align_model(language_code="en",device=device)
    result=whisperx.align(raw["segments"],align_model,metadata,audio,device,return_char_alignments=False)
    observed=[]
    for seg in result.get("segments",[]): observed.extend(seg.get("words",[]))
    observed=[w for w in observed if w.get("start") is not None and w.get("end") is not None and _norm(str(w.get("word","")))]
    canonical=_canonical_tokens(voice_plan,normalized); bound=_bind_tokens(canonical,observed)
    timings=[{k:v for k,v in x.items() if k!="text"} for x in bound]
    return {"version":"m6.9-whisperx-production-v2","word_timings":timings,
        "coverage":{"expected_words":len(canonical),"aligned_words":len(timings),"observed_words":len(observed),"exact_normalized_stream":True}}
