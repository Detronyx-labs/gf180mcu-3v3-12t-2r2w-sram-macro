proc mark {msg} {
    set fp [open $::env(STEP_LOG) a]
    puts $fp $msg
    close $fp
}
crashbackups stop
drc off
set topcell $::env(MAGIC_TOPCELL)
mark {gds read begin}
gds read $::env(GDS_PATH)
mark {gds read done}
load $topcell
select top cell
expand
extract style ngspice()
mark {extract unique begin}
extract unique
mark {extract unique done}
extract path $::env(EXT_DIR)
extract no all
mark {extract all begin}
extract all
mark {extract all done}
ext2sim labels on
mark {ext2sim begin}
ext2sim -p $::env(EXT_DIR) $topcell
mark {ext2sim done}
ext2spice lvs
ext2spice blackbox off
mark {ext2spice lvs begin}
ext2spice -p $::env(EXT_DIR) -o $::env(PEX_LVS_SPICE)
mark {ext2spice lvs done}
quit -noprompt
