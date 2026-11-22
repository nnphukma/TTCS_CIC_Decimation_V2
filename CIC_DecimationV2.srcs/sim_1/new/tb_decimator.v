`timescale 1ns / 1ps

module tb_decimator;

    localparam integer R     = 16;
    localparam integer WIDTH = 28;
    localparam real    CLK_PERIOD = 10.0;

    reg                      clk;
    reg                      rst_n;
    reg                      valid_in;
    reg  signed [WIDTH-1:0]  data_in;
    wire                     valid_out;
    wire signed [WIDTH-1:0]  data_out;

    reg signed [WIDTH-1:0] expected_mem [0:2];
    reg                    prev_valid_out;
    integer out_idx;
    integer k;

    decimator #(
        .R     (R),
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
        expected_mem[0] = 28'sd1015; // mẫu thứ 16 (index 15)
        expected_mem[1] = 28'sd1031; // mẫu thứ 32 (index 31)
        expected_mem[2] = 28'sd1047; // mẫu thứ 48 (index 47)
    end

    always @(posedge clk) begin
        if (!rst_n) begin
            prev_valid_out <= 1'b0;
        end else begin
            prev_valid_out <= valid_out;

            if (^valid_out === 1'bx) begin
                $display("[FAIL] tb_decimator: valid_out chua gia tri X/Z tai t=%0t", $time);
                $fatal(1);
            end

            // Kiểm tra valid_out không bao giờ giữ mức 1 quá 1 chu kỳ clock
            if (valid_out === 1'b1 && prev_valid_out === 1'b1) begin
                $display("[FAIL] tb_decimator: valid_out keo dai hon 1 chu ky clock tai t=%0t", $time);
                $fatal(1);
            end

            if (valid_out === 1'b1) begin
                if (^data_out === 1'bx) begin
                    $display("[FAIL] tb_decimator: data_out chua gia tri X/Z tai mau %0d", out_idx);
                    $fatal(1);
                end
                if (out_idx >= 3) begin
                    $display("[FAIL] tb_decimator: Phat sinh thua output tai mau %0d", out_idx);
                    $fatal(1);
                end
                if (data_out !== expected_mem[out_idx]) begin
                    $display("[FAIL] tb_decimator: Mismatch tai mau %0d | Expected = %0d, Got = %0d",
                             out_idx, expected_mem[out_idx], data_out);
                    $fatal(1);
                end
                out_idx = out_idx + 1;
            end
        end
    end

    initial begin
        out_idx  = 0;
        rst_n    = 1'b0;
        valid_in = 1'b0;
        data_in  = {WIDTH{1'b0}};
        repeat (12) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);

        // Gửi 48 mẫu hợp lệ, xen kẽ 3 chu kỳ idle có dữ liệu nhiễu khi valid_in = 0
        for (k = 0; k < 48; k = k + 1) begin
            @(negedge clk);
            valid_in = 1'b1;
            data_in  = 28'sd1000 + k;

            @(negedge clk);
            valid_in = 1'b0;
            data_in  = 28'h5555555; // Dữ liệu rác khi valid_in = 0 (không được phép nhận)
            repeat (2) @(negedge clk);
        end

        repeat (6) @(negedge clk);

        if (out_idx !== 3) begin
            $display("[FAIL] tb_decimator: Thieu output | Expected = 3, Got = %0d", out_idx);
            $fatal(1);
        end

        $display("==================================================");
        $display("RESULT: PASS - tb_decimator (3/3 samples match)");
        $display("==================================================");
        $finish;
    end

endmodule