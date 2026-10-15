#!/usr/bin/env python3
"""Animatic: the locked timing built only from the approved still (every shot is a stand-in).

It is a timing reference for the AI clips and a "plan B" rough cut.  Thin wrapper around assemble.py:
  python3 production/tools/make_animatic.py --ep E01
writes production/<EP>/animatic/<EP>_animatic_clean.mp4 and <EP>_animatic_labeled.mp4.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--ep", default="E01"); a, _ = ap.parse_known_args()
    assemble.run(["--ep", a.ep, "--standin-only", "--both", "--quality", "draft",
                  "--out-dir", f"{assemble.ROOT}/production/{a.ep}/animatic", "--name", f"{a.ep}_animatic"])
