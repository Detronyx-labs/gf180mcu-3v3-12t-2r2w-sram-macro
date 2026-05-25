// Structural blackbox wrapper for the RC7 custom-gate control matrix.
// Folded address contract: addr[2:0] selects one of 8 data groups;
// addr[8:3] selects one of 64 physical wordline rows.
module gf180mcu_3v3_12t_2r2w_sram_512x8_stdcell_control_matrix (
    input  logic VDD,
    input  logic VSS,
    input  logic w0_en,
    input  logic w1_en,
    input  logic r0_en,
    input  logic r1_en,
    output logic write_conflict,
    input  logic [8:0] w0_addr,
    input  logic [8:0] w1_addr,
    input  logic [8:0] r0_addr,
    input  logic [8:0] r1_addr,
    output logic [63:0] w0_wl,
    output logic [63:0] w1_wl,
    output logic [63:0] r0_wl,
    output logic [63:0] r1_wl,
    output logic [7:0] w0_grp,
    output logic [7:0] w1_grp,
    output logic [7:0] r0_grp,
    output logic [7:0] r1_grp
);
endmodule
