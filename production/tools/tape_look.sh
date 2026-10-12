#!/usr/bin/env bash
# Applies the "recorded on tape" look to a 9:16 video: slight RGB split, grain, scanlines, soft contrast, vignette.
# Usage: production/tools/tape_look.sh in.mp4 out.mp4
# Strength can be tuned with env vars:  GRAIN=16 SPLIT=3 SCAN=0.9
set -euo pipefail
IN="${1:?input file}"; OUT="${2:?output file}"
GRAIN="${GRAIN:-16}"; SPLIT="${SPLIT:-3}"; SCAN="${SCAN:-0.9}"
ffmpeg -y -loglevel error -i "$IN" -vf \
"scale=1080:1920:flags=lanczos,format=gbrp,rgbashift=rh=${SPLIT}:bh=-${SPLIT},format=yuv420p,\
eq=contrast=1.04:saturation=0.85:brightness=0.01,\
geq=lum='lum(X,Y)*if(eq(mod(Y,3),0),${SCAN},1)':cb='cb(X,Y)':cr='cr(X,Y)',\
noise=alls=${GRAIN}:allf=t,vignette=angle=PI/5" \
-c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy "$OUT"
