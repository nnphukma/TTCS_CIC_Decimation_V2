`timescale 1ns / 1ps

module tb_comb;

    localparam integer N     = 4;
    localparam integer M     = 1;
    localparam integer WIDTH = 28;
    localparam real    CLK_PERIOD = 10.0;

    reg                      clk;
    reg                      rst_n;
    reg                      valid_in;
    reg  signed [WIDTH-1:0]  data_in;
    wire                     valid_out;
    wire signed [WIDTH-1:0]  data_out;

    // 12 mẫu kỳ vọng (6 impulse + 6 constant DC cho Comb bậc N=4)
    reg signed [WIDTH-1:0] expected_mem [0:11];
    integer out_idx;
    integer err_cnt;
    integer i;

    comb #(
        .N     (N),
        .M     (M),
        .WIDTH (WIDTH)
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
        // Test 1: Impulse = 100 -> [100, -400, 600, -400, 100, 0]
        expected_mem[0]  =  28'sd100;
        expected_mem[1]  = -28'sd400;
        expected_mem[2]  =  28'sd600;
        expected_mem[3]  = -28'sd400;
        expected_mem[4]  =  28'sd100;
        expected_mem[5]  =  28'sd0;

        // Test 2: Constant DC = 500 (Comb bậc 4: 4 mẫu quá độ rồi về 0)
        expected_mem[6]  =  28'sd500;
        expected_mem[7]  = -28'sd1500;
        expected_mem[8]  =  28'sd1500;
        expected_mem[9]  = -28'sd500;
        expected_mem[10] =  28'sd0;
        expected_mem[11] =  28'sd0;
    end

    task apply_reset;
        begin
            rst_n    = 1'b0;
            valid_in = 1'b0;
            data_in  = {WIDTH{1'b0}};
            repeat (12) @(negedge clk);
            rst_n = 1'b1;
            repeat (2) @(negedge clk);
        end
    endtask

    task send_sample;
        input signed [WIDTH-1:0] sample_val;
        input integer idle_cycles;
        begin
            @(negedge clk);
            valid_in = 1'b1;
            data_in  = sample_val;
            @(negedge clk);
            valid_in = 1'b0;
            data_in  = {WIDTH{1'b0}};
            if (idle_cycles > 0) begin
                repeat (idle_cycles) @(negedge clk);
            end
        end
    endtask

    always @(posedge clk) begin
        if (rst_n) begin
            if (^valid_out === 1'bx) begin
                $display("[FAIL] tb_comb: valid_out chua gia tri X/Z tai t=%0t", $time);
                err_cnt = err_cnt + 1;
                $fatal(1);
            end
            if (valid_out === 1'b1) begin
                if (^data_out === 1'bx) begin
                    $display("[FAIL] tb_comb: data_out chua gia tri X/Z tai mau %0d", out_idx);
                    err_cnt = err_cnt + 1;
                    $fatal(1);
                end
                if (out_idx >= 12) begin
                    $display("[FAIL] tb_comb: Phat sinh thua output tai mau %0d", out_idx);
                    err_cnt = err_cnt + 1;
                    $fatal(1);
                end
                if (data_out !== expected_mem[out_idx]) begin
                    $display("[FAIL] tb_comb: Mismatch tai mau %0d | Expected = %0d, Got = %0d",
                             out_idx, expected_mem[out_idx], data_out);
                    err_cnt = err_cnt + 1;
                    $fatal(1);
                end
                out_idx = out_idx + 1;
            end
        end
    end

    initial begin
        out_idx = 0;
        err_cnt = 0;

        // --- TEST 1: IMPULSE = 100 ---
        apply_reset();
        send_sample(28'sd100, 4);
        for (i = 0; i < 5; i = i + 1) begin
            send_sample(28'sd0, 4);
        end
        repeat (6) @(negedge clk);

        // --- TEST 2: CONSTANT DC = 500 (back-to-back) ---
        apply_reset();
        for (i = 0; i < 6; i = i + 1) begin
            send_sample(28'sd500, 0);
        end
        repeat (8) @(negedge clk);

        if (out_idx !== 12 || err_cnt !== 0) begin
            $display("[FAIL] tb_comb: Tong loi = %0d | Samples = %0d/12", err_cnt, out_idx);
            $fatal(1);
        end

        $display("==================================================");
        $display("RESULT: PASS - tb_comb (12/12 samples match, 0 errors)");
        $display("==================================================");
        $finish;
    end

endmodule