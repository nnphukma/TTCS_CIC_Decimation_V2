`timescale 1ns / 1ps

module tb_cic_decimator;

    localparam integer N          = 4;
    localparam integer R          = 16;
    localparam integer M          = 1;
    localparam integer W_IN       = 12;
    localparam integer W_OUT      = 12;
    localparam integer NUM_IN     = 5000;
    localparam integer NUM_OUT    = NUM_IN / R; // 312
    localparam integer CLK_DIV    = 100;        // 100 MHz / 1 MHz = 100 clocks
    localparam real    CLK_PERIOD = 10.0;       // 10 ns (100 MHz)

    reg                       clk;
    reg                       rst_n;
    reg                       valid_in;
    reg  signed [W_IN-1:0]    data_in;
    wire                      valid_out;
    wire signed [W_OUT-1:0]   data_out;

    reg [W_IN-1:0]  stimulus_mem [0:NUM_IN-1];
    reg [W_OUT-1:0] expected_mem [0:NUM_OUT-1];

    reg     prev_valid_out;
    integer out_idx;
    integer err_cnt;
    integer in_idx;
    integer fd_out;

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
        $readmemh("stimulus.mem", stimulus_mem);
        $readmemh("expected.mem", expected_mem);

        if (^stimulus_mem[0] === 1'bx || ^expected_mem[0] === 1'bx) begin
            $display("[FAIL] tb_cic_decimator: Khong doc duoc stimulus.mem hoac expected.mem!");
            $fatal(1);
        end
    end

    always @(posedge clk) begin
        if (!rst_n) begin
            prev_valid_out <= 1'b0;
        end else begin
            prev_valid_out <= valid_out;

            if (^valid_out === 1'bx) begin
                $display("[FAIL] tb_cic_decimator: valid_out chua X/Z tai t=%0t", $time);
                err_cnt = err_cnt + 1;
                $fatal(1);
            end

            if (valid_out === 1'b1 && prev_valid_out === 1'b1) begin
                $display("[FAIL] tb_cic_decimator: valid_out keo dai hon 1 chu ky clock tai t=%0t", $time);
                err_cnt = err_cnt + 1;
                $fatal(1);
            end

            if (valid_out === 1'b1) begin
                if (^data_out === 1'bx) begin
                    $display("[FAIL] tb_cic_decimator: data_out chua X/Z tai mau %0d", out_idx);
                    err_cnt = err_cnt + 1;
                    $fatal(1);
                end

                if (out_idx >= NUM_OUT) begin
                    $display("[FAIL] tb_cic_decimator: Phat sinh thua output (mau %0d >= %0d)", out_idx, NUM_OUT);
                    err_cnt = err_cnt + 1;
                    $fatal(1);
                end

                $fwrite(fd_out, "%03X\n", data_out);

                if (data_out !== expected_mem[out_idx]) begin
                    $display("[FAIL] tb_cic_decimator: Mismatch tai mau %0d | Expected = 0x%03X (%0d), Got = 0x%03X (%0d)",
                             out_idx,
                             expected_mem[out_idx], $signed(expected_mem[out_idx]),
                             data_out, data_out);
                    err_cnt = err_cnt + 1;
                    $fatal(1);
                end

                out_idx = out_idx + 1;
            end
        end
    end

    initial begin
        out_idx  = 0;
        err_cnt  = 0;
        rst_n    = 1'b0;
        valid_in = 1'b0;
        data_in  = {W_IN{1'b0}};

        fd_out = $fopen("rtl_output.mem", "w");
        if (fd_out == 0) begin
            $display("[FAIL] tb_cic_decimator: Khong mo duoc file rtl_output.mem de ghi!");
            $fatal(1);
        end

        repeat (12) @(negedge clk);
        rst_n = 1'b1;
        repeat (5) @(negedge clk);

        for (in_idx = 0; in_idx < NUM_IN; in_idx = in_idx + 1) begin
            @(negedge clk);
            valid_in = 1'b1;
            data_in  = stimulus_mem[in_idx];

            @(negedge clk);
            valid_in = 1'b0;
            data_in  = {W_IN{1'b0}};

            repeat (CLK_DIV - 2) @(negedge clk);
        end

        // Chờ 200 chu kỳ clock xả hết 8 tầng pipeline latency của Option B
        repeat (200) @(negedge clk);
        $fclose(fd_out);

        $display("--------------------------------------------------");
        $display("Expected outputs : %0d", NUM_OUT);
        $display("Received outputs : %0d", out_idx);
        $display("Error count      : %0d", err_cnt);

        if (out_idx !== NUM_OUT || err_cnt !== 0) begin
            $display("RESULT: FAIL - tb_cic_decimator");
            $fatal(1);
        end

        $display("Matched outputs  : %0d/%0d", out_idx, NUM_OUT);
        $display("RESULT: PASS - All output samples match expected.mem.");
        $display("--------------------------------------------------");
        $finish;
    end

    initial begin
        #6_000_000;
        $display("[FAIL] tb_cic_decimator: Simulation TIMEOUT tai t=%0t!", $time);
        $fatal(1);
    end

endmodule