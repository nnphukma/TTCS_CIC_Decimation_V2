// -----------------------------------------------------------------------------
// decimator.v
// Counts valid input samples and emits one registered output sample for every
// R accepted input samples.
//
// data_out is captured on the same clock edge that accepts the R-th sample.
// valid_out is asserted for one clock period after that edge. Capturing data
// together with valid prevents a later upstream update from changing the sample
// seen by the following Comb stage.
// -----------------------------------------------------------------------------

`timescale 1ns / 1ps

module decimator #(
    parameter integer R     = 16,
    parameter integer WIDTH = 28
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         valid_in,
    input  wire signed [WIDTH-1:0]      data_in,
    output reg                          valid_out,
    output reg  signed [WIDTH-1:0]     data_out
);

    localparam integer COUNT_WIDTH = (R <= 1) ? 1 : $clog2(R);
    localparam [COUNT_WIDTH-1:0] LAST_COUNT = R - 1;

    reg [COUNT_WIDTH-1:0] sample_count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sample_count <= {COUNT_WIDTH{1'b0}};
            valid_out    <= 1'b0;
            data_out     <= {WIDTH{1'b0}};
        end else begin
            // Default: output-valid is a one-cycle pulse.
            valid_out <= 1'b0;

            if (valid_in) begin
                if (sample_count == LAST_COUNT) begin
                    sample_count <= {COUNT_WIDTH{1'b0}};
                    valid_out    <= 1'b1;
                    data_out     <= data_in;
                end else begin
                    sample_count <= sample_count + 1'b1;
                end
            end
        end
    end

endmodule
