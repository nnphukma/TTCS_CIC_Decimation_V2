## ============================================================================
## Ràng buộc vật lý & Thời gian cho CIC Decimation Filter (Option B)
## Board: Digilent Arty A7-100T (xc7a100tcsg324-1)
## ============================================================================

## 1. Xung nhịp hệ thống 100 MHz (Oscillator E3)
set_property -dict {PACKAGE_PIN E3 IOSTANDARD LVCMOS33} [get_ports clk]
create_clock -period 10.000 -name sys_clk -waveform {0.000 5.000} [get_ports clk]

## 2. Tín hiệu điều khiển (BTN0 = rst_n, BTN1 = valid_in, LD0 = valid_out)
set_property -dict {PACKAGE_PIN D9 IOSTANDARD LVCMOS33} [get_ports rst_n]
set_property -dict {PACKAGE_PIN C9 IOSTANDARD LVCMOS33} [get_ports valid_in]
set_property -dict {PACKAGE_PIN H5 IOSTANDARD LVCMOS33} [get_ports valid_out]

## 3. Bus dữ liệu đầu vào data_in[11:0] -> Pmod JA (8-bit thấp) & Pmod JB (4-bit cao)
set_property -dict {PACKAGE_PIN G13 IOSTANDARD LVCMOS33} [get_ports {data_in[0]}]
set_property -dict {PACKAGE_PIN B11 IOSTANDARD LVCMOS33} [get_ports {data_in[1]}]
set_property -dict {PACKAGE_PIN A11 IOSTANDARD LVCMOS33} [get_ports {data_in[2]}]
set_property -dict {PACKAGE_PIN D12 IOSTANDARD LVCMOS33} [get_ports {data_in[3]}]
set_property -dict {PACKAGE_PIN D13 IOSTANDARD LVCMOS33} [get_ports {data_in[4]}]
set_property -dict {PACKAGE_PIN B18 IOSTANDARD LVCMOS33} [get_ports {data_in[5]}]
set_property -dict {PACKAGE_PIN A18 IOSTANDARD LVCMOS33} [get_ports {data_in[6]}]
set_property -dict {PACKAGE_PIN K16 IOSTANDARD LVCMOS33} [get_ports {data_in[7]}]

set_property -dict {PACKAGE_PIN E15 IOSTANDARD LVCMOS33} [get_ports {data_in[8]}]
set_property -dict {PACKAGE_PIN E16 IOSTANDARD LVCMOS33} [get_ports {data_in[9]}]
set_property -dict {PACKAGE_PIN D15 IOSTANDARD LVCMOS33} [get_ports {data_in[10]}]
set_property -dict {PACKAGE_PIN C15 IOSTANDARD LVCMOS33} [get_ports {data_in[11]}]

## 4. Bus dữ liệu đầu ra data_out[11:0] -> Pmod JC (8-bit thấp) & Pmod JD (4-bit cao)
set_property -dict {PACKAGE_PIN U12 IOSTANDARD LVCMOS33} [get_ports {data_out[0]}]
set_property -dict {PACKAGE_PIN V12 IOSTANDARD LVCMOS33} [get_ports {data_out[1]}]
set_property -dict {PACKAGE_PIN V10 IOSTANDARD LVCMOS33} [get_ports {data_out[2]}]
set_property -dict {PACKAGE_PIN V11 IOSTANDARD LVCMOS33} [get_ports {data_out[3]}]
set_property -dict {PACKAGE_PIN U14 IOSTANDARD LVCMOS33} [get_ports {data_out[4]}]
set_property -dict {PACKAGE_PIN V14 IOSTANDARD LVCMOS33} [get_ports {data_out[5]}]
set_property -dict {PACKAGE_PIN T13 IOSTANDARD LVCMOS33} [get_ports {data_out[6]}]
set_property -dict {PACKAGE_PIN U13 IOSTANDARD LVCMOS33} [get_ports {data_out[7]}]

set_property -dict {PACKAGE_PIN D4  IOSTANDARD LVCMOS33} [get_ports {data_out[8]}]
set_property -dict {PACKAGE_PIN D3  IOSTANDARD LVCMOS33} [get_ports {data_out[9]}]
set_property -dict {PACKAGE_PIN F4  IOSTANDARD LVCMOS33} [get_ports {data_out[10]}]
set_property -dict {PACKAGE_PIN F3  IOSTANDARD LVCMOS33} [get_ports {data_out[11]}]

## 5. Ngoại lệ Timing cho các cổng I/O không đồng bộ tốc độ thấp (BTN/LED/Pmod)
set_false_path -from [get_ports {rst_n valid_in data_in[*]}]
set_false_path -to   [get_ports {valid_out data_out[*]}]