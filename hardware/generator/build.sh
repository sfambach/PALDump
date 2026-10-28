#!/bin/sh
# Builds schematic, board (Freerouting) and DRC report: sh build.sh shield
# Needs KiCad 7 (pcbnew Python), Java, xvfb-run and the Freerouting 1.9 jar ($FREEROUTING).
set -e
export KICAD7_FOOTPRINT_DIR=${KICAD7_FOOTPRINT_DIR:-/usr/share/kicad/footprints}
export KICAD7_SYMBOL_DIR=${KICAD7_SYMBOL_DIR:-/usr/share/kicad/symbols}
cd "$(dirname "$0")"
B=${1:-shield}
H=$(cd .. && pwd)/$B
T=${TMPDIR:-/tmp}/paldump-$B
mkdir -p $H $T
N=paldump-$B
cat > $H/fp-lib-table <<'X'
(fp_lib_table
  (version 7)
  (lib (name "arduino-library")(type "KiCad")(uri "${KIPRJMOD}/../lib/arduino-library.pretty")(options "")(descr "Alarm-Siren arduino-kicad-library, CC BY-SA 4.0"))
)
X
cat > $H/sym-lib-table <<'X'
(sym_lib_table
  (version 7)
  (lib (name "arduino-library")(type "KiCad")(uri "${KIPRJMOD}/../lib/arduino-library.kicad_sym")(options "")(descr "Alarm-Siren arduino-kicad-library, CC BY-SA 4.0"))
  (lib (name "paldump")(type "KiCad")(uri "${KIPRJMOD}/../lib/paldump.kicad_sym")(options "")(descr "ZIF socket with PAL pin roles"))
)
X
python3 mklib.py >/dev/null
python3 mksch.py $B $H/$N.kicad_sch
kicad-cli sch export netlist -o $T/net.net $H/$N.kicad_sch >/dev/null
python3 verify.py $B $T/net.net
[ "$2" = "sch" ] && exit 0
rm -f $T/route.kicad_pro $H/$N.kicad_pro
python3 mkpcb.py $B $T/route.kicad_pcb
python3 -c "import pcbnew;b=pcbnew.LoadBoard('$T/route.kicad_pcb');pcbnew.ExportSpecctraDSN(b,'$T/route.dsn')"
rm -f $T/route.ses
(cd $T && timeout 1500 xvfb-run -a java -jar ${FREEROUTING:-/opt/tools/freerouting.jar} -de $T/route.dsn -do $T/route.ses -mp ${PASSES:-60} 2>&1 | grep -E "completed|unrouted|incomplete" | tail -3)
python3 finish.py $B $T/route.kicad_pcb $T/route.ses $H/$N.kicad_pcb
python3 labels.py $B $H/$N.kicad_pcb
python3 -c "import pcbnew;b=pcbnew.LoadBoard('$H/$N.kicad_pcb');pcbnew.WriteDRCReport(b,'$H/drc-report.txt',pcbnew.EDA_UNITS_MILLIMETRES,True)"
grep -E "^\[" $H/drc-report.txt | sed 's/\]:.*/]/' | sort | uniq -c || true
grep -E "unconnected pads" $H/drc-report.txt
