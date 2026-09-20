#!/usr/bin/env python3
"""M6.3 fail-closed structural/semantic VoicePlan validator."""
from __future__ import annotations

from dataclasses import dataclass

ROLES={"HOOK","QUESTION","CONTRAST","IMPORTANT_FACT","REVEAL","EXPLANATION","TRANSITION","CONCLUSION"}
INTENTS={"engage","ask","contrast","inform","reveal","explain","bridge","close"}
EMOTIONS={"neutral","curious","confident","warm","serious"}
PITCH={"level","rise","fall","rise-fall"}
CONTOURS={"neutral","question-rise","declarative-fall","contrastive","reveal-arc"}

@dataclass(frozen=True)
class VoicePlanError:
    code:str
    path:str
    message:str

class VoicePlanValidationError(ValueError):
    def __init__(self, errors:list[VoicePlanError]):
        self.errors=errors
        super().__init__("; ".join(f"{e.code}@{e.path}: {e.message}" for e in errors))
    def as_dict(self):
        return {"valid":False,"errors":[e.__dict__ for e in self.errors]}

def validate_voice_plan(plan:dict, normalized:dict|None=None, known_pronunciations:set[str]|None=None)->dict:
    errors=[]
    def err(code,path,msg): errors.append(VoicePlanError(code,path,msg))
    if plan.get("schema_version")!=1: err("VERSION","schema_version","expected 1")
    if plan.get("voice_plan_version")!="m6.2-v1": err("VERSION","voice_plan_version","unsupported VoicePlan version")
    if normalized is not None:
        for k in ("normalizer_version","lexicon_version","lexicon_sha256","display_text","spoken_text"):
            if plan.get(k)!=normalized.get(k): err("PROVENANCE",k,"does not match normalized source")
    display=plan.get("display_text")
    spoken=plan.get("spoken_text")
    if not isinstance(display,str): err("TYPE","display_text","must be string"); display=""
    if not isinstance(spoken,str): err("TYPE","spoken_text","must be string"); spoken=""
    blocks=plan.get("blocks")
    if not isinstance(blocks,list) or not blocks:
        err("COVERAGE","blocks","must contain at least one block"); blocks=[]
    expected_s=0
    previous_d=0
    seen_ids=set()
    for i,b in enumerate(blocks):
        p=f"blocks[{i}]"
        if not isinstance(b,dict): err("TYPE",p,"must be object"); continue
        bid=b.get("block_id")
        if not isinstance(bid,str) or bid in seen_ids: err("BLOCK_ID",p+".block_id","missing or duplicate block id")
        seen_ids.add(bid)
        if b.get("role") not in ROLES: err("ROLE",p+".role","unsupported semantic role")
        if b.get("intent") not in INTENTS: err("INTENT",p+".intent","unsupported intent")
        if b.get("emotion") not in EMOTIONS: err("EMOTION",p+".emotion","unsupported emotion")
        if b.get("pitch_direction") not in PITCH: err("PITCH",p+".pitch_direction","unsupported pitch direction")
        if b.get("intonation_contour") not in CONTOURS: err("CONTOUR",p+".intonation_contour","unsupported contour")
        for key,lo,hi in (("target_wpm",120,210),("rate",.8,1.2),("pre_pause_ms",0,1200),("post_pause_ms",0,1200),("energy",.25,.75),("pitch_range_semitones",0,4)):
            v=b.get(key)
            if not isinstance(v,(int,float)) or isinstance(v,bool) or not lo<=v<=hi: err("BOUNDS",p+"."+key,f"must be within {lo}..{hi}")
        ss=b.get("spoken_span",{}); ds=b.get("display_span",{})
        s0,s1=ss.get("start"),ss.get("end"); d0,d1=ds.get("start"),ds.get("end")
        if not all(isinstance(x,int) for x in (s0,s1)) or not (0<=s0<s1<=len(spoken)):
            err("SPAN",p+".spoken_span","invalid spoken span")
        else:
            if s0!=expected_s: err("COVERAGE",p+".spoken_span",f"expected start {expected_s}")
            expected_s=s1
        if not all(isinstance(x,int) for x in (d0,d1)) or not (0<=d0<=d1<=len(display)):
            err("SPAN",p+".display_span","invalid display span")
        elif d0<previous_d: err("ORDER",p+".display_span","display spans reordered")
        else: previous_d=d1
        for j,e in enumerate(b.get("emphasis",[])):
            es=e.get("spoken_span",{}) if isinstance(e,dict) else {}
            if not isinstance(e,dict) or e.get("strength") not in {"light","moderate"} or not all(isinstance(es.get(k),int) for k in ("start","end")) or not (s0<=es.get("start",-1)<es.get("end",-1)<=s1): err("EMPHASIS",f"{p}.emphasis[{j}]","malformed or outside block")
        for j,pause in enumerate(b.get("internal_pauses",[])):
            if not isinstance(pause,dict) or not isinstance(pause.get("after_spoken_offset"),int) or not isinstance(pause.get("ms"),int) or not (s0<=pause.get("after_spoken_offset",-1)<=s1) or not 40<=pause.get("ms",-1)<=800: err("PAUSE",f"{p}.internal_pauses[{j}]","invalid internal pause")
        refs=b.get("pronunciation_refs",[])
        if not isinstance(refs,list): err("PRONUNCIATION",p+".pronunciation_refs","must be list")
        elif known_pronunciations is not None:
            for ref in refs:
                if ref not in known_pronunciations: err("PRONUNCIATION",p+".pronunciation_refs",f"unknown reference: {ref}")
    if blocks and expected_s!=len(spoken): err("COVERAGE","blocks",f"spoken coverage ends at {expected_s}, expected {len(spoken)}")
    if errors: raise VoicePlanValidationError(errors)
    return {"valid":True,"errors":[]}
