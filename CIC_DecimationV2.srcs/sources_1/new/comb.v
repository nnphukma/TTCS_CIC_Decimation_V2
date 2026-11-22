// -----------------------------------------------------------------------------
// comb.v
// CIC Comb cascade with one registered pipeline stage per Comb section.
//
// Each section computes:
//     y_stage[n] = x_stage[n] - x_stage[n-M]
//
// Every section has its own M-sample delay line. valid_pipe transports the
// sample-valid pulse through the registered Comb stages. Each stage therefore
// processes the current sample from the preceding stage, not its previous
// sample's value.
//
// Arithmetic is WIDTH-bit two's-complement modular arithmetic (wrap-around).
// -----------------------------------------------------------------------------

`timescale 1ns / 1ps

module comb #(
    parameter integer N     = 4,
    parameter integer M     = 1,
    parameter integer WIDTH = 28
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         valid_in,
    input  wire signed [WIDTH-1:0]      data_in,
    output wire                         valid_out,
    output wire signed [WIDTH-1:0]      data_out
);

    reg signed [WIDTH-1:0] stage_data [0:N-1];
    reg signed [WIDTH-1:0] delay_mem  [0:N*M-1];
    reg        [N-1:0]     valid_pipe;

    integer i;
    integer j;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_pipe <= {N{1'b0}};

            for (i = 0; i < N; i = i + 1) begin
                stage_data[i] <= {WIDTH{1'b0}};
            end

            for (j = 0; j < N*M; j = j + 1) begin
                delay_mem[j] <= {WIDTH{1'b0}};
            end
        end else begin
            // Comb stage 0 consumes the decimated input.
            valid_pipe[0] <= valid_in;
            if (valid_in) begin
                stage_data[0] <= data_in - delay_mem[M-1];

                // Shift this stage's M-sample delay line.
                for (j = M-1; j > 0; j = j - 1) begin
                    delay_mem[j] <= delay_mem[j-1];
                end
                delay_mem[0] <= data_in;
            end

            // Remaining Comb stages consume the registered result from the
            // preceding stage one clock later.
            for (i = 1; i < N; i = i + 1) begin
                valid_pipe[i] <= valid_pipe[i-1];

                if (valid_pipe[i-1]) begin
                    stage_data[i] <= stage_data[i-1]
                                     - delay_mem[i*M + M-1];

                    // Shift this stage's independent M-sample delay line.
                    for (j = M-1; j > 0; j = j - 1) begin
                        delay_mem[i*M + j] <= delay_mem[i*M + j - 1];
                    end
                    delay_mem[i*M] <= stage_data[i-1];
                end
            end
        end
    end

    assign valid_out = valid_pipe[N-1];
    assign data_out  = stage_data[N-1];

endmodule
