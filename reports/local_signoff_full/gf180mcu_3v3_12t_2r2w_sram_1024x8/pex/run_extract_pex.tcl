crashbackups stop
drc off
set topcell $::env(MAGIC_TOPCELL)
load $topcell
select top cell
expand
extract style ngspice()
extract unique
extract path $::env(EXT_DIR)
extract no all
extract all
ext2sim labels on
ext2sim -p $::env(EXT_DIR) $topcell
extresist threshold 0
extresist tolerance 10
extresist extout on
extresist silent on
if {[info exists ::env(PEX_NETS)] && $::env(PEX_NETS) ne ""} {
    eval extresist include $::env(PEX_NETS)
}
extresist all
ext2spice lvs
ext2spice blackbox on
ext2spice -p $::env(EXT_DIR) -o $::env(PEX_LVS_SPICE)
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice extresist on
ext2spice resistor tee on
ext2spice blackbox on
ext2spice -p $::env(EXT_DIR) -o $::env(PEX_RC_SPICE)
quit -noprompt
