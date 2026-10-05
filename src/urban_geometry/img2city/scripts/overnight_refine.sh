#!/bin/bash
# Overnight driver for `img2city.city.generate --refine-all`: run the refinement
# batch, and when the subscription hits the model's usage limit mid-run, wait and
# poll until the quota resets, then resume (refine-all is resumable). When every
# building is refined, rebuild the scene. Safe to leave running unattended: it
# never switches models on its own, and a no-progress stall aborts it rather
# than spinning.
#
#   scripts/overnight_refine.sh <area-dir> [MIN-AREA] [MODEL]      (ITERS=n env)
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
PY=${PYTHON:-python3}
OUT=${1:-data/city_sk}
MINAREA=${2:-200}
RLOG=$OUT/refine_all.log
# model: argument 3, else the configured spec model (.env / IMG2CITY_SPEC_MODEL)
MODEL=${3:-$($PY -c "from img2city import config; print(config.SPEC_MODEL)")}
CITY="$PY -m img2city.city.generate"

now(){ $PY -c 'import datetime;print(datetime.datetime.now().strftime("%H:%M:%S"))'; }
say(){ echo "[driver $(now)] $*"; }

remaining(){ $CITY --out "$OUT" --min-area "$MINAREA" --refine-status 2>/dev/null | awk '/REMAINING/{print $2}'; }
model_up(){ $PY -c "from img2city.agent.llm import healthcheck; ok,why=healthcheck('$MODEL'); print('OK' if ok else 'DOWN '+why)"; }

prev=-1; stall=0
while true; do
  REM=$(remaining)
  if [ -z "$REM" ]; then say "could not read remaining count -- retrying in 5m"; sleep 300; continue; fi
  say "remaining=$REM"
  [ "$REM" = "0" ] && { say "all buildings refined"; break; }

  HC=$(model_up)
  if [ "${HC%% *}" = "OK" ]; then
    # model available: an attempt that makes NO progress here is a real stall
    # (Blender down, persistent render error), so count it and abort after 3.
    # Waiting for a quota reset does NOT count -- that path never reaches this branch.
    if [ "$REM" = "$prev" ]; then
      stall=$((stall+1))
      say "model up but no progress since last attempt (stall $stall/3)"
      [ "$stall" -ge 3 ] && { say "ABORT: 3 no-progress attempts while the model was UP -- check Blender/BlenderMCP is still open. Scene will be reassembled from saved specs."; break; }
    else
      stall=0
    fi
    prev=$REM
    say "model available -> running refine-all on $REM building(s)"
    $CITY --out "$OUT" --min-area "$MINAREA" --refine-all --model "$MODEL" --refine-iters "${ITERS:-3}" >> "$RLOG" 2>&1
    say "refine-all attempt exited (rc=$?)"
    sleep 30
  else
    # capped: expected while waiting for the session/quota reset -- just wait, never
    # treat this as a stall
    say "model capped (${HC#OK }) -- waiting 20m for quota reset"
    sleep 1200
  fi
done

say "rebuilding block scene from refined specs"
$CITY --out "$OUT" --min-area 0 --assemble-only >> "$RLOG" 2>&1   # ALWAYS 0: MINAREA scopes REFINE, not assembly
say "reassemble rc=$?"
FINAL=$(remaining)
say "DRIVER_DONE remaining=$FINAL"
