#!/bin/sh
# Exports gerbers (ZIP), schematic PDF and top/bottom renders: sh outputs.sh shield
set -e
cd "$(dirname "$0")"
B=${1:-shield}
H=$(cd .. && pwd)/$B
N=paldump-$B
T=${TMPDIR:-/tmp}/paldump-out-$B
rm -rf "${T:?}" && mkdir -p $T/gerber
kicad-cli pcb export gerbers -o $T/gerber/ -l F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts $H/$N.kicad_pcb >/dev/null
kicad-cli pcb export drill -o $T/gerber/ $H/$N.kicad_pcb >/dev/null
rm -f $H/$N-gerber.zip
(cd $T/gerber && python3 -c "import zipfile,os,sys;z=zipfile.ZipFile(sys.argv[1],'w',zipfile.ZIP_DEFLATED);[z.write(f) for f in sorted(os.listdir('.'))]" $H/$N-gerber.zip)
kicad-cli sch export pdf -o $H/$N-schematic.pdf $H/$N.kicad_sch >/dev/null
kicad-cli sch export svg -o $T $H/$N.kicad_sch >/dev/null
python3 -c "import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2],output_width=3000,background_color='white')" $T/$N.svg $H/$N-schematic.png
kicad-cli pcb export svg -o $T/top.svg -l F.Cu,F.Silkscreen,F.Mask,Edge.Cuts --page-size-mode 2 --exclude-drawing-sheet $H/$N.kicad_pcb >/dev/null
kicad-cli pcb export svg -o $T/bottom.svg -l B.Cu,B.Silkscreen,B.Mask,Edge.Cuts --mirror --page-size-mode 2 --exclude-drawing-sheet $H/$N.kicad_pcb >/dev/null
for s in top bottom; do
  python3 -c "import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2],output_width=1600,background_color='white')" $T/$s.svg $H/$N-$s.png
done
ls -la $H | grep -E "zip|pdf|png"
