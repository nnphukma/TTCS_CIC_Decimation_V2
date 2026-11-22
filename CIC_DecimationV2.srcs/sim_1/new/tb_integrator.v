`timescale 1ns / 1ps

module tb_integrator;

    localparam integer N     = 4;
    localparam integer WIDTH = 28;
    localparam real    CLK_PERIOD = 10.0;

    reg                      clk;
    reg                      rst_n;
    reg                      valid_in;
    reg  signed [WIDTH-1:0]  data_in;
    wire                     valid_out;
    wire signed [WIDTH-1:0]  data_out;

    // 17 mẫu kỳ vọng cho 3 bài test (6 impulse + 6 constant + 5 ramp)
    reg signed [WIDTH-1:0] expected_mem [0:16];
    integer out_idx;
    integer i;

    integrator #(
        .N     (N),
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

    // Khởi tạo bảng giá trị kỳ vọng
    initial begin
        // Test 1: Impulse (6 mẫu)
        expected_mem[0]  = 28'sd1;
        expected_mem[1]  = 28'sd4;
        expected_mem[2]  = 28'sd10;
        expected_mem[3]  = 28'sd20;
        expected_mem[4]  = 28'sd35;
        expected_mem[5]  = 28'sd56;

        // Test 2: Constant = 1 (6 mẫu)
        expected_mem[6]  = 28'sd1;
        expected_mem[7]  = 28'sd5;
        expected_mem[8]  = 28'sd15;
        expected_mem[9]  = 28'sd35;
        expected_mem[10] = 28'sd70;
        expected_mem[11] = 28'sd126;

        // Test 3: Ramp = 1..5 (5 mẫu)
        expected_mem[12] = 28'sd1;
        expected_mem[13] = 28'sd6;
        expected_mem[14] = 28'sd21;
        expected_mem[15] = 28'sd56;
        expected_mem[16] = 28'sd126;
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

    // Monitor tự kiểm tra tại cạnh lên clock
    always @(posedge clk) begin
        if (rst_n) begin
            if (^valid_out === 1'bx) begin
                $display("[FAIL] tb_integrator: valid_out chua gia tri X/Z tai t=%0t", $time);
                $fatal(1);
            end
            if (valid_out === 1'b1) begin
                if (^data_out === 1'bx) begin
                    $display("[FAIL] tb_integrator: data_out chua gia tri X/Z tai mau %0d", out_idx);
                    $fatal(1);
                end
                if (out_idx >= 17) begin
                    $display("[FAIL] tb_integrator: Phat sinh thua output tai mau %0d", out_idx);
                    $fatal(1);
                end
                if (data_out !== expected_mem[out_idx]) begin
                    $display("[FAIL] tb_integrator: Mismatch tai mau %0d | Expected = %0d, Got = %0d",
                             out_idx, expected_mem[out_idx], data_out);
                    $fatal(1);
                end
                out_idx = out_idx + 1;
            end
        end
    end

    initial begin
        out_idx = 0;

        // --- TEST 1: IMPULSE (cách nhau 4 clock idle) ---
        apply_reset();
        send_sample(28'sd1, 4);
        for (i = 0; i < 5; i = i + 1) begin
            send_sample(28'sd0, 4);
        end
        repeat (6) @(negedge clk);

        // --- TEST 2: CONSTANT = 1 (chạy liên tiếp back-to-back để kiểm tra pipeline) ---
        apply_reset();
        for (i = 0; i < 6; i = i + 1) begin
            send_sample(28'sd1, 0);
        end
        repeat (8) @(negedge clk);

        // --- TEST 3: RAMP = 1, 2, 3, 4, 5 ---
        apply_reset();
        for (i = 1; i <= 5; i = i + 1) begin
            send_sample(i, 2);
        end
        repeat (8) @(negedge clk);

        if (out_idx !== 17) begin
            $display("[FAIL] tb_integrator: Thieu output | Expected = 17, Got = %0d", out_idx);
            $fatal(1);
        end

        $display("==================================================");
        $display("RESULT: PASS - tb_integrator (17/17 samples match)");
        $display("==================================================");
        $finish;
    end

endmodule