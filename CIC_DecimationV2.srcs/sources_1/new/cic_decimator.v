// -----------------------------------------------------------------------------
// cic_decimator.v
// Top-level Nth-order CIC decimator using registered Integrator and Comb
// pipeline stages (Option B).
//
// Default configuration:
//   N=4, R=16, M=1, W_IN=12, W_OUT=12
//   f_clk=100 MHz, f_sample=1 MHz (input valid every 100 clocks)
//   f_out=62.5 kHz
//
// Internal arithmetic width:
//   W_INT = W_IN + N*ceil(log2(R*M))
//
// Output scaling preserves the previous project's convention: take the most
// significant W_OUT bits of the full-width Comb result. No rounding or
// saturation is performed.
// -----------------------------------------------------------------------------

`timescale 1ns / 1ps

module cic_decimator #(
    parameter integer N     = 4,
    parameter integer R     = 16,
    parameter integer M     = 1,
    parameter integer W_IN  = 12,
    parameter integer W_OUT = 12
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         valid_in,
    input  wire signed [W_IN-1:0]      data_in,
    output wire                         valid_out,
    output wire signed [W_OUT-1:0]     data_out
);

    localparam integer W_GROWTH = N * $clog2(R*M);
    localparam integer W_INT    = W_IN + W_GROWTH;

    wire signed [W_INT-1:0] data_in_ext;

    wire                         integrator_valid;
    wire signed [W_INT-1:0]      integrator_data;

    wire                         decimator_valid;
    wire signed [W_INT-1:0]      decimator_data;

    wire                         comb_valid;
    wire signed [W_INT-1:0]      comb_data;

    // Sign-extend the external input to the full internal CIC width.
    assign data_in_ext = {{(W_INT-W_IN){data_in[W_IN-1]}}, data_in};

    // High-rate Integrator cascade. Each stage is a registered pipeline stage.
    integrator #(
        .N     (N),
        .WIDTH (W_INT)
    ) u_integrator (
        .clk       (clk),
        .rst_n     (rst_n),
        .valid_in  (valid_in),
        .data_in   (data_in_ext),
        .valid_out (integrator_valid),
        .data_out  (integrator_data)
    );

    // Decimation counts completed Integrator samples and captures the selected
    // full-width sample together with its valid pulse.
    decimator #(
        .R     (R),
        .WIDTH (W_INT)
    ) u_decimator (
        .clk       (clk),
        .rst_n     (rst_n),
        .valid_in  (integrator_valid),
        .data_in   (integrator_data),
        .valid_out (decimator_valid),
        .data_out  (decimator_data)
    );

    // Low-rate Comb cascade. Each section is a registered pipeline stage.
    comb #(
        .N     (N),
        .M     (M),
        .WIDTH (W_INT)
    ) u_comb (
        .clk       (clk),
        .rst_n     (rst_n),
        .valid_in  (decimator_valid),
        .data_in   (decimator_data),
        .valid_out (comb_valid),
        .data_out  (comb_data)
    );

    assign valid_out = comb_valid;

    // Full-precision result is reduced to W_OUT bits by MSB truncation.
    assign data_out = comb_data[W_INT-1 : W_INT-W_OUT];

endmodule
