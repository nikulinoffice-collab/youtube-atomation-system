#!/usr/bin/env python3
"""M6.9 real WhisperX alignment bridge for the production Ryan path."""
from __future__ import annotations
import re
from pathlib import Path
class ProductionAlignmentError(RuntimeError): pass
def _norm(s:str)->str: return re.sub(r"[^a-z0-9']+","",s.casefold())
def _lexical_spans(text:str): return [(m.start(),m.end(),m.group(0)) for m in re.finditer(r"(?:[$€£]?[0-9]+(?:[.,][0-9]+)*(?:[KMB])?|[^\W_]+(?:['’][^\W_]+)*)",text,re.UNICODE|re.IGNORECASE)]
def _spoken_to_display(n:dict,pos:int,*,end=False)->int:
 d=n["display_text"]; dc=sc=0
 for m in n.get("mappings",[]):
  unchanged=m["spoken_start"]-sc
  if pos<=sc+unchanged:return min(len(d),dc+pos-sc)
  dc+=unchanged;sc+=unchanged
  if pos<=m["spoken_end"]:return m["display_end"] if end or pos==m["spoken_end"] else m["display_start"]
  dc=m["display_end"];sc=m["spoken_end"]
 return min(len(d),dc+pos-sc)
def _emit_group(out,cg,og):
 start=float(og[0]["start"]);end=float(og[-1]["end"]);total=sum(max(1,len(_norm(x["text"]))) for x in cg);cursor=start;used=0;score=min(float(x.get("score",1)) for x in og)
 for k,item in enumerate(cg):
  used+=max(1,len(_norm(item["text"])));te=end if k==len(cg)-1 else start+(end-start)*used/total;out.append({**item,"start_s":cursor,"end_s":te,"confidence":score});cursor=te
def _bind_tokens(canonical,observed):
 out=[];ci=oi=0
 while ci<len(canonical) and oi<len(observed):
  # WhisperX may render a normalized spoken expansion in its original display form
  # (e.g. spoken "twenty twenty six" observed as "2026").  Accept that only when
  # provenance proves all consumed canonical tokens map to the exact same display token.
  span=canonical[ci].get("display_span_id");display=_norm(str(canonical[ci].get("display_text","")));ow=_norm(str(observed[oi]["word"]))
  if span and display and ow==display:
   cj=ci+1
   while cj<len(canonical) and canonical[cj].get("display_span_id")==span:cj+=1
   _emit_group(out,canonical[ci:cj],[observed[oi]]);ci=cj;oi+=1;continue
  c0=ci;o0=oi;cs=os=""
  while not(cs==os and cs):
   if (len(cs)<=len(os) and ci<len(canonical)) or oi>=len(observed):cs+=_norm(canonical[ci]["text"]);ci+=1
   elif oi<len(observed):os+=_norm(str(observed[oi]["word"]));oi+=1
   else:break
   if cs and os and not(cs.startswith(os) or os.startswith(cs)):raise ProductionAlignmentError(f"WHISPERX_TOKEN_MISMATCH: canonical={cs!r} observed={os!r}")
  if not cs or cs!=os:raise ProductionAlignmentError(f"WHISPERX_COVERAGE_MISMATCH: canonical={cs!r} observed={os!r}")
  _emit_group(out,canonical[c0:ci],observed[o0:oi])
 if ci!=len(canonical) or oi!=len(observed):raise ProductionAlignmentError(f"WHISPERX_COVERAGE_MISMATCH: canonical_remaining={len(canonical)-ci} observed_remaining={len(observed)-oi}")
 return out
def _canonical_tokens(vp,n):
 ds=_lexical_spans(vp["display_text"]);out=[]
 for block in vp["blocks"]:
  s0=block["spoken_span"]["start"];s1=block["spoken_span"]["end"];idx=0
  for a,b,text in _lexical_spans(vp["spoken_text"][s0:s1]):
   sa=s0+a;sb=s0+b;da=_spoken_to_display(n,sa);db=_spoken_to_display(n,sb,end=True);cand=[(i,x) for i,x in enumerate(ds) if x[0]<max(db,da+1) and x[1]>da]
   if not cand:raise ProductionAlignmentError(f"DISPLAY_MAPPING_MISSING: spoken={text!r}")
   di,dsp=cand[0];out.append({"block_id":block["block_id"],"spoken_span_id":f"spoken:{block['spoken_span']['start']}:{block['spoken_span']['end']}","display_span_id":f"display-token:{di}:{dsp[0]}:{dsp[1]}","token_index":idx,"spoken_text":text,"display_text":vp["display_text"][dsp[0]:dsp[1]],"text":text});idx+=1
 return out
def align(wav_path:Path,voice_plan:dict,normalized:dict|None=None,*,device="cpu")->dict:
 if normalized is None:
  from scripts.m6_voice_script import normalize
  normalized=normalize(voice_plan["display_text"])
 if normalized["spoken_text"]!=voice_plan["spoken_text"]:raise ProductionAlignmentError("NORMALIZATION_PROVENANCE_MISMATCH")
 try:import whisperx
 except Exception as exc:raise ProductionAlignmentError(f"WHISPERX_IMPORT_FAILED: {exc}") from exc
 audio=whisperx.load_audio(str(wav_path));model=whisperx.load_model("tiny.en",device,compute_type="int8");raw=model.transcribe(audio,batch_size=4,language="en");am,meta=whisperx.load_align_model(language_code="en",device=device);res=whisperx.align(raw["segments"],am,meta,audio,device,return_char_alignments=False);obs=[]
 for seg in res.get("segments",[]):obs.extend(seg.get("words",[]))
 obs=[w for w in obs if w.get("start") is not None and w.get("end") is not None and _norm(str(w.get("word","")))];can=_canonical_tokens(voice_plan,normalized);bound=_bind_tokens(can,obs);tim=[{k:v for k,v in x.items() if k!="text"} for x in bound]
 return {"version":"m6.9-whisperx-production-v3","word_timings":tim,"coverage":{"expected_words":len(can),"aligned_words":len(tim),"observed_words":len(obs),"exact_normalized_stream":True}}
