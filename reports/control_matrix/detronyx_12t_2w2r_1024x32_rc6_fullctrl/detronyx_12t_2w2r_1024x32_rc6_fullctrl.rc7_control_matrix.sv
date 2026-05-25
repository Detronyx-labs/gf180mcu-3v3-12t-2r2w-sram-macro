// Structural blackbox wrapper for the RC7 custom-gate control matrix.
// Folded address contract: addr[1:0] selects one of 4 data groups;
// addr[9:2] selects one of 256 physical wordline rows.
module detronyx_12t_2w2r_1024x32_rc6_fullctrl_rc7_control_matrix (
    input  logic VDD,
    input  logic VSS,
    input  logic w0_en,
    input  logic w1_en,
    input  logic r0_en,
    input  logic r1_en,
    output logic write_conflict,
    input  logic [9:0] w0_addr,
    input  logic [9:0] w1_addr,
    input  logic [9:0] r0_addr,
    input  logic [9:0] r1_addr,
    output logic [255:0] w0_wl,
    output logic [255:0] w1_wl,
    output logic [255:0] r0_wl,
    output logic [255:0] r1_wl,
    output logic [3:0] w0_grp,
    output logic [3:0] w1_grp,
    output logic [3:0] r0_grp,
    output logic [3:0] r1_grp
);
endmodule
