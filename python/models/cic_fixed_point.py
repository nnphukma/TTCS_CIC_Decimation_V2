"""
cic_fixed_point.py
Mô hình Fixed-Point Bit-Accurate khớp 100% với RTL Option B:
- Số học bù 2 độ rộng W_INT = 28-bit tràn vòng (modular wrap-around).
- Không bão hòa (no saturation), không làm tròn (no rounding).
- Cắt bit đầu ra: comb_data[27:16] (MSB truncation).
Xuất đồ thị: reports/figures/02_cic_fixed_point_comparison.png
"""

import math
import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
sys.path.insert(0, str(PYTHON_DIR))


def wrap_signed(val: int, bits: int) -> int:
    """Ép số nguyên Python về miền số học bù 2 có dấu độ rộng `bits` (tràn vòng)."""
    mask = (1 << bits) - 1
    sign_bit = 1 << (bits - 1)
    v = int(val) & mask
    return v - (1 << bits) if (v & sign_bit) else v


def int_to_hex(val: int, bits: int) -> str:
    """Chuyển số nguyên có dấu sang chuỗi hex bù 2 viết hoa (không có tiền tố 0x)."""
    mask = (1 << bits) - 1
    hex_digits = math.ceil(bits / 4)
    return f"{int(val) & mask:0{hex_digits}X}"


def hex_to_int(hex_str: str, bits: int) -> int:
    """Đọc chuỗi hex bù 2 từ file .mem về số nguyên Python có dấu."""
    raw = int(hex_str.strip(), 16)
    return wrap_signed(raw, bits)


def cic_decimate_fixed(
    x_in: np.ndarray,
    N: int = 4,
    R: int = 16,
    M: int = 1,
    w_in: int = 12,
    w_out: int = 12,
) -> np.ndarray:
    """
    Mô phỏng bit-exact từng chu kỳ mẫu của CIC Decimator Option B.
    """
    w_growth = N * math.ceil(math.log2(R * M))
    w_int = w_in + w_growth
    shift_bits = w_int - w_out

    int_state = [0] * N
    comb_delay = [[0] * M for _ in range(N)]

    sample_count = 0
    outputs = []

    for raw_sample in x_in:
        x_val = wrap_signed(int(raw_sample), w_in)
        acc = wrap_signed(x_val, w_int)

        # 1. Chuỗi N tầng Integrator
        for i in range(N):
            int_state[i] = wrap_signed(int_state[i] + acc, w_int)
            acc = int_state[i]

        # 2. Decimator: đếm 0 .. R-1, chốt mẫu tại R-1
        if sample_count == R - 1:
            sample_count = 0
            comb_in = acc

            # 3. Chuỗi N tầng Comb
            for i in range(N):
                delayed_sample = comb_delay[i][M - 1]
                comb_out = wrap_signed(comb_in - delayed_sample, w_int)

                for j in range(M - 1, 0, -1):
                    comb_delay[i][j] = comb_delay[i][j - 1]
                comb_delay[i][0] = comb_in

                comb_in = comb_out

            # 4. Cắt W_OUT bit cao: comb_data[W_INT-1 : W_INT-W_OUT]
            truncated = comb_in >> shift_bits
            outputs.append(wrap_signed(truncated, w_out))
        else:
            sample_count += 1

    return np.array(outputs, dtype=np.int64)


def main() -> None:
    from models.cic_model import cic_decimate_float

    N, R, M, W_IN, W_OUT = 4, 16, 1, 12, 12
    fs = 1_000_000.0
    n = np.arange(5000)
    x_test = np.round(1000.0 * np.sin(2.0 * np.pi * 10_000.0 * n / fs)).astype(np.int64)

    y_fix = cic_decimate_fixed(x_test, N=N, R=R, M=M, w_in=W_IN, w_out=W_OUT)
    y_flt = cic_decimate_float(x_test, N=N, R=R, M=M, normalize_gain=True)

    err = y_fix - y_flt
    print("=== KIỂM TRA FIXED-POINT BIT-ACCURATE (BƯỚC 1d) ===")
    print(f"Số mẫu đầu ra  : {len(y_fix)}")
    print(f"Sai số min/max so với float (LSB): [{np.min(err):.6f}, {np.max(err):.6f}]")
    assert np.min(err) >= -1.0 and np.max(err) <= 0.0 + 1e-12, "Lỗi phép cắt bit!"
    print("KẾT LUẬN: PASS (Sai số lượng tử hóa nằm chuẩn trong [-1, 0] LSB).")

    # Vẽ đồ thị đối chiếu Floating-Point vs Fixed-Point
    fig_dir = PROJECT_ROOT / "reports" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig_path = fig_dir / "02_cic_fixed_point_comparison.png"

    fig, axes = plt.subplots(2, 1, figsize=(10.5, 7.2), dpi=150)

    # Subplot 1: Dạng sóng đầu ra (Zoom 80 mẫu đầu tiên)
    k_zoom = np.arange(80)
    axes[0].plot(k_zoom, y_flt[:80], color="#1f77b4", linewidth=1.8, label="Floating-Point Reference (float64)")
    axes[0].step(k_zoom, y_fix[:80], where="mid", color="#ff7f0e", linestyle="--", linewidth=1.4, label="Fixed-Point Bit-Accurate (12-bit [27:16])")
    axes[0].set_title("So sánh đáp ứng miền thời gian: Floating-Point vs Fixed-Point (Tín hiệu Sin 10 kHz)")
    axes[0].set_xlabel("Chỉ số mẫu đầu ra (k)")
    axes[0].set_ylabel("Biên độ đầu ra (LSB)")
    axes[0].grid(True, linestyle=":", alpha=0.7)
    axes[0].legend(loc="upper right")

    # Subplot 2: Sai số lượng tử hóa trên toàn bộ 312 mẫu
    k_all = np.arange(len(err))
    axes[1].plot(k_all, err, color="#2ca02c", linewidth=1.0, marker=".", markersize=3, label="Sai số e[k] = y_fixed[k] - y_float[k]")
    axes[1].axhline(0.0, color="#d62728", linestyle="--", linewidth=1.2, label="Biên trên lý thuyết (0 LSB)")
    axes[1].axhline(-1.0, color="#9467bd", linestyle="--", linewidth=1.2, label="Biên dưới lý thuyết (-1 LSB - MSB Truncation)")
    axes[1].set_title(f"Phân bố sai số cắt bit 12-bit trên 312 mẫu (Min = {np.min(err):.4f} LSB, Max = {np.max(err):.4f} LSB)")
    axes[1].set_xlabel("Chỉ số mẫu đầu ra (k)")
    axes[1].set_ylabel("Sai số (LSB)")
    axes[1].set_ylim([-1.25, 0.25])
    axes[1].grid(True, linestyle=":", alpha=0.7)
    axes[1].legend(loc="lower right")

    plt.tight_layout()
    plt.savefig(fig_path, dpi=300, bbox_inches="tight")
    print(f"Đã lưu đồ thị tại: {fig_path}")
    plt.show()


if __name__ == "__main__":
    main()