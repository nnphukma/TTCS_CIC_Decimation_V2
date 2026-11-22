`timescale 1ns / 1ps

module tb_cic_decimator_sine;

    localparam integer N          = 4;
    localparam integer R          = 16;
    localparam integer M          = 1;
    localparam integer W_IN       = 12;
    localparam integer W_OUT      = 12;
    localparam integer NUM_IN     = 5000;
    localparam integer NUM_OUT    = NUM_IN / R; // 312
    localparam integer CLK_DIV    = 100;
    localparam real    CLK_PERIOD = 10.0;

    reg                       clk;
    reg                       rst_n;
    reg                       valid_in;
    reg  signed [W_IN-1:0]    data_in;
    wire                      valid_out;
    wire signed [W_OUT-1:0]   data_out;

    reg [W_IN-1:0] stimulus_sine_mem [0:NUM_IN-1];

    integer out_idx;
    integer in_idx;
    integer fd_sine;

    cic_decimator #(
        .N     (N),
        .R     (R),
        .M     (M),
        .W_IN  (W_IN),
        .W_OUT (W_OUT)
    ) dut (
        .clk       (clk),
        .rst_n     (rst_n),
        .valid_in  (valid_in),
        .data_in   (data_in),
        .valid_out (valid_out),
        .data_out  (data_out)
    );

    initial clk = 1'b0;
    always #(CLK_PERIOD / 2.0) clk = ~clk;

    initial begin
        $readmemh("stimulus_sine.mem", stimulus_sine_mem);
        if (^stimulus_sine_mem[0] === 1'bx) begin
            $display("[FAIL] tb_cic_decimator_sine: Khong doc duoc stimulus_sine.mem!");
            $fatal(1);
        end
    end

    always @(posedge clk) begin
        if (rst_n) begin
            if (^valid_out === 1'bx) begin
                $display("[FAIL] tb_cic_decimator_sine: valid_out chua X/Z tai t=%0t", $time);
                $fatal(1);
            end
            if (valid_out === 1'b1) begin
                if (^data_out === 1'bx) begin
                    $display("[FAIL] tb_cic_decimator_sine: data_out chua X/Z tai mau %0d", out_idx);
                    $fatal(1);
                end
                if (out_idx >= NUM_OUT) begin
                    $display("[FAIL] tb_cic_decimator_sine: Phat sinh thua output tai mau %0d", out_idx);
                    $fatal(1);
                end
                $fwrite(fd_sine, "%03X\n", data_out);
                out_idx = out_idx + 1;
            end
        end
    end

    initial begin
        out_idx  = 0;
        rst_n    = 1'b0;
        valid_in = 1'b0;
        data_in  = {W_IN{1'b0}};

        fd_sine = $fopen("rtl_sine_output.mem", "w");
        if (fd_sine == 0) begin
            $display("[FAIL] tb_cic_decimator_sine: Khong mo duoc file rtl_sine_output.mem!");
            $fatal(1);
        end

        repeat (12) @(negedge clk);
        rst_n = 1'b1;
        repeat (5) @(negedge clk);

        for (in_idx = 0; in_idx < NUM_IN; in_idx = in_idx + 1) begin
            @(negedge clk);
            valid_in = 1'b1;
            data_in  = stimulus_sine_mem[in_idx];

            @(negedge clk);
            valid_in = 1'b0;
            data_in  = {W_IN{1'b0}};

            repeat (CLK_DIV - 2) @(negedge clk);
        end

        repeat (200) @(negedge clk);
        $fclose(fd_sine);

        if (out_idx !== NUM_OUT) begin
            $display("[FAIL] tb_cic_decimator_sine: Thieu output | Expected = %0d, Got = %0d", NUM_OUT, out_idx);
            $fatal(1);
        end

        $display("==================================================");
        $display("RESULT: PASS - tb_cic_decimator_sine (%0d/%0d samples exported)", out_idx, NUM_OUT);
        $display("==================================================");
        $finish;
    end

    initial begin
        #6_000_000;
        $display("[FAIL] tb_cic_decimator_sine: Simulation TIMEOUT!");
        $fatal(1);
    end

endmodule