#!/bin/sh
# Builds the firmware on the host against the simulated socket, once per wiring and PAL type, and compares the dumps.
set -e
cd "$(dirname "$0")"
S=../../source/PALDump_2560
T=${TMPDIR:-/tmp}/paldump-sim
mkdir -p $T
for w in 0 1; do
  for t in 16 20; do
    sed "s/^int simType = 16;/int simType = $t;/" sim.cpp > $T/sim_$t.cpp
    g++ -O2 -w -I. -I$S -DPALDUMP_SHIELD=$w -DGLOBAL_PAL_TYPE=PAL${t}L8 -include Arduino.h -o $T/sim_${w}_$t \
      $T/sim_$t.cpp $S/PALDump.cpp -x c++ $S/PALDump_2560.ino
    $T/sim_${w}_$t | grep -v "PALDump shield" > $T/out_${w}_$t.txt
  done
done
for t in 16 20; do
  if cmp -s $T/out_0_$t.txt $T/out_1_$t.txt; then echo "PAL${t}L8: shield dump == original wiring dump ($(grep -c '^[01]' $T/out_1_$t.txt) lines)"
  else echo "PAL${t}L8: DIFFERENT"; diff $T/out_0_$t.txt $T/out_1_$t.txt | head -20; exit 1; fi
done
