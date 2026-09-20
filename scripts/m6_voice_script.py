#!/usr/bin/env python3
"""M6.1 deterministic display_text -> spoken_text normalizer.

The canonical display text is never mutated. Every replacement records the exact
source display span so later alignment can map spoken audio back to captions.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEXICON_PATH = ROOT / "config/m6/pronunciation_lexicon.v1.json"

ONES = ["zero","one","two","three","four","five","six","seven","eight","nine","ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen","eighteen","nineteen"]
TENS = ["","","twenty","thirty","forty","fifty","sixty","seventy","eighty","ninety"]

def int_words(n: int) -> str:
    if n < 0: return "minus " + int_words(-n)
    if n < 20: return ONES[n]
    if n < 100: return TENS[n//10] + (" " + ONES[n%10] if n%10 else "")
    if n < 1000: return ONES[n//100] + " hundred" + (" " + int_words(n%100) if n%100 else "")
    for value, name in ((1_000_000_000,"billion"),(1_000_000,"million"),(1000,"thousand")):
        if n >= value:
            return int_words(n//value)+" "+name+(" "+int_words(n%value) if n%value else "")
    raise ValueError("integer outside supported range")

def decimal_words(raw: str) -> str:
    left, dot, right = raw.replace(",", "").partition(".")
    out = int_words(int(left))
    if dot: out += " point " + " ".join(ONES[int(c)] for c in right)
    return out

def year_words(raw: str) -> str:
    y=int(raw)
    if 2000 <= y <= 2009: return "two thousand" + (" " + int_words(y-2000) if y>2000 else "")
    if 2010 <= y <= 2099: return "twenty " + int_words(y-2000)
    return int_words(y)

def load_lexicon(path: Path = LEXICON_PATH):
    raw=path.read_bytes(); data=json.loads(raw)
    return data, hashlib.sha256(raw).hexdigest()

def normalize(display_text: str, lexicon_path: Path = LEXICON_PATH) -> dict:
    lex, lex_hash=load_lexicon(lexicon_path)
    rules=[]
    for e in lex["entries"]:
        rules.append((re.compile(r"(?<!\w)"+re.escape(e["display"])+r"(?!\w)"), lambda m,e=e:e["spoken"], "lexicon:"+e["kind"]))
    rules += [
      (re.compile(r"\$([0-9][0-9,]*(?:\.[0-9]+)?)([MB])\b"), lambda m: decimal_words(m.group(1))+ (" million dollars" if m.group(2)=="M" else " billion dollars"), "currency_compact"),
      (re.compile(r"\$([0-9][0-9,]*(?:\.[0-9]+)?)"), lambda m: decimal_words(m.group(1))+" dollars", "currency"),
      (re.compile(r"\b([0-9][0-9,]*(?:\.[0-9]+)?)%"), lambda m: decimal_words(m.group(1))+" percent", "percent"),
      (re.compile(r"\b(20[0-9]{2})\b"), lambda m: year_words(m.group(1)), "year"),
      (re.compile(r"\b([0-9]+\.[0-9]+)\b"), lambda m: decimal_words(m.group(1)), "decimal"),
      (re.compile(r"\b([0-9]+)\b"), lambda m: int_words(int(m.group(1))), "integer")]
    # Build non-overlapping edits against immutable canonical text. Earlier rules win.
    edits=[]; occupied=[]
    for pattern, fn, kind in rules:
        for m in pattern.finditer(display_text):
            if any(not (m.end() <= a or m.start() >= b) for a,b in occupied): continue
            spoken=fn(m)
            if spoken != m.group(0):
                edits.append((m.start(),m.end(),spoken,kind,m.group(0))); occupied.append((m.start(),m.end()))
    edits.sort()
    pieces=[]; mappings=[]; dpos=spos=0
    for a,b,repl,kind,src in edits:
        unchanged=display_text[dpos:a]; pieces.append(unchanged); spos += len(unchanged)
        ss=spos; pieces.append(repl); spos += len(repl)
        mappings.append({"display_start":a,"display_end":b,"spoken_start":ss,"spoken_end":spos,"display":src,"spoken":repl,"rule":kind})
        dpos=b
    pieces.append(display_text[dpos:])
    spoken_text="".join(pieces)
    return {"schema_version":1,"normalizer_version":"m6.1-v1","lexicon_version":lex["lexicon_version"],"lexicon_sha256":lex_hash,"display_text":display_text,"spoken_text":spoken_text,"mappings":mappings}

def validate(result: dict) -> None:
    assert result["display_text"] is not None
    prev_d=prev_s=0
    for m in result["mappings"]:
        assert m["display_start"] >= prev_d and m["spoken_start"] >= prev_s
        assert result["display_text"][m["display_start"]:m["display_end"]] == m["display"]
        assert result["spoken_text"][m["spoken_start"]:m["spoken_end"]] == m["spoken"]
        prev_d=m["display_end"]; prev_s=m["spoken_end"]

def main():
    p=argparse.ArgumentParser(); p.add_argument("text"); args=p.parse_args()
    result=normalize(args.text); validate(result); print(json.dumps(result,indent=2,ensure_ascii=False))
if __name__ == "__main__": main()
