// -----------------------------------------------------------------------------
// integrator.v
// CIC integrator cascade with one registered pipeline stage per integrator.
//
// Each input sample is accumulated by stage 0, then propagated through stages
// 1..N-1 on successive clocks. valid_pipe keeps each sample aligned with its
// corresponding data value. The pipeline accepts one sample per clock.
//
// Arithmetic is WIDTH-bit two's-complement modular arithmetic (wrap-around).
// -----------------------------------------------------------------------------

`timescale 1ns / 1ps

module integrator #(
    parameter integer N     = 4,
    parameter integer WIDTH = 28
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         valid_in,
    input  wire signed [WIDTH-1:0]      data_in,
    output wire                         valid_out,
    output wire signed [WIDTH-1:0]      data_out
);

    reg signed [WIDTH-1:0] stage_state [0:N-1];
    reg        [N-1:0]     valid_pipe;

    integer i;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_pipe <= {N{1'b0}};
            for (i = 0; i < N; i = i + 1) begin
                stage_state[i] <= {WIDTH{1'b0}};
            end
        end else begin
            // Stage 0 consumes the external input sample.
            valid_pipe[0] <= valid_in;
            if (valid_in) begin
                stage_state[0] <= stage_state[0] + data_in;
            end

            // Every following stage consumes the previous stage's registered
            // result one clock later. The delayed valid bit identifies the
            // same sample at each pipeline stage.
            for (i = 1; i < N; i = i + 1) begin
                valid_pipe[i] <= valid_pipe[i-1];
                if (valid_pipe[i-1]) begin
                    stage_state[i] <= stage_state[i] + stage_state[i-1];
                end
            end
        end
    end

    assign valid_out = valid_pipe[N-1];
    assign data_out  = stage_state[N-1];

endmodule
