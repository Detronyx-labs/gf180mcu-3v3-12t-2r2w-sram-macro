crashbackups stop
drc off
set topcell $::env(MAGIC_TOPCELL)
load $topcell
select top cell
expand
gds write ../layout/$topcell.gds
extract style ngspice()
extract unique
extract path extfiles
extract no all
extract all
ext2spice lvs
ext2spice -p extfiles -o ../layout/$topcell.current_pdk.spice
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice -p extfiles -o ../layout/$topcell.current_pdk_rc.spice
quit -noprompt
