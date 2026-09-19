#!/usr/bin/env python3
"""Build M6.0 engine-neutral blind listening and separate audit manifests."""
from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path

ENGINES={
 "edge_legacy":{"artifact_dir":"edge","version":"edge-tts==7.2.7","config":{"voice":"en-US-GuyNeural","rate":"+0%"}},
 "kokoro":{"artifact_dir":"kokoro","version":"kokoro==0.9.4","config":{"voice":"af_heart","speed":1.0}},
 "chatterbox_nano":{"artifact_dir":"chatterbox","version":"5de7a54aa4e5e2baadb0182dde554908b48b85c2","config":{"nano":True,"device":"cpu","reference_voice":"builtin_default"}},
}
CASES=("hook","question","contrast","important_fact","reveal","neutral","numbers_dates","acronyms","versions_units","long_sentence","paragraphs","short_30s")

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def find_audio(root,case):
    xs=list(root.rglob(case+".wav"))
    if len(xs)!=1: raise SystemExit(f"expected one {case}.wav under {root}, got {len(xs)}")
    return xs[0]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--inputs",type=Path,required=True); ap.add_argument("--out",type=Path,required=True); a=ap.parse_args()
    corpus=json.loads(Path("docs/m6/benchmark_corpus.json").read_text())
    frozen=json.loads(Path("docs/m6/frozen_corpus_manifest.json").read_text())
    source={x["id"]:x["text_sha256"] for x in frozen["cases"]}
    texts={x["id"]:x["text"] for x in corpus["cases"]}
    review=a.out/"review"; audit=a.out/"audit"; audio=review/"audio"
    audio.mkdir(parents=True,exist_ok=True); audit.mkdir(parents=True,exist_ok=True)
    reviewer=[]; binding=[]
    for case in CASES:
      if hashlib.sha256(texts[case].encode()).hexdigest()!=source[case]: raise SystemExit("source mismatch "+case)
      for engine,meta in ENGINES.items():
        src=find_audio(a.inputs/meta["artifact_dir"],case); ah=sha(src)
        sid="sample_"+hashlib.sha256(("m6blind:v1:"+engine+":"+case+":"+ah).encode()).hexdigest()[:16]
        dst=audio/(sid+".wav"); shutil.copyfile(src,dst)
        reviewer.append({"sample_id":sid,"case_id":case,"source_text":texts[case],"source_text_sha256":source[case],"audio_sha256":ah})
        binding.append({"sample_id":sid,"case_id":case,"engine_id":engine,"engine_version_or_commit":meta["version"],"config":meta["config"],"source_text_sha256":source[case],"audio_sha256":ah})
    if len(reviewer)!=36 or len({x["sample_id"] for x in reviewer})!=36: raise SystemExit("blind matrix incomplete")
    review_manifest={"schema_version":"1.0","milestone":"M6.0","status":"HUMAN_LISTENING_INPUT","engine_names_exposed":False,"sample_count":36,"production_changed":False,"samples":reviewer}
    rb=json.dumps(review_manifest,indent=2,sort_keys=True)+"\n"; (review/"blind_review_manifest.json").write_text(rb)
    review_hash=hashlib.sha256(rb.encode()).hexdigest()
    audit_manifest={"schema_version":"1.0","milestone":"M6.0","review_manifest_sha256":review_hash,"sample_count":36,"production_changed":False,"paid_services_used":False,"bindings":binding}
    ab=json.dumps(audit_manifest,indent=2,sort_keys=True)+"\n"; (audit/"blind_audit_binding.json").write_text(ab)
    (review/"README.txt").write_text("M6.0 BLIND LISTENING\nListen using sample IDs only. Do not inspect the separate audit artifact until scoring is complete. 12 cases x 3 engines = 36 samples.\n")
    print(json.dumps({"status":"PASS","samples":36,"review_manifest_sha256":review_hash,"audit_manifest_sha256":hashlib.sha256(ab.encode()).hexdigest()}))
if __name__=="__main__": main()
