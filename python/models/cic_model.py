"""
cic_model.py
Mô hình tham chiếu Floating-Point cho bộ lọc CIC Decimation (Bước 1a).
Cấu trúc: N tầng Integrator -> Decimator (R) -> N tầng Comb.
Xuất đồ thị: reports/figures/01_cic_floating_point_response.png
"""

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def cic_decimate_float(
    x: np.ndarray,
    N: int = 4,
    R: int = 16,
    M: int = 1,
    normalize_gain: bool = True,
) -> np.ndarray:
    """
    Mô phỏng bộ lọc CIC Decimation bằng số thực dấu phẩy động (float64).
    Pha lấy mẫu giảm tần tại chỉ số n = k*R + (R - 1) để khớp 100% với decimator.v.
    """
    x_arr = np.asarray(x, dtype=np.float64)

    # 1. N tầng Integrator nối tầng (High-rate fs)
    int_out = x_arr.copy()
    for _ in range(N):
        int_out = np.cumsum(int_out)

    # 2. Decimation với hệ số R: chốt mẫu thứ R của mỗi nhóm (index R-1, 2R-1, ...)
    dec_out = int_out[R - 1 :: R]

    # 3. N tầng Comb nối tầng với độ trễ vi sai M (Low-rate fs/R)
    comb_out = dec_out.copy()
    for _ in range(N):
        delayed = np.zeros_like(comb_out)
        if len(comb_out) > M:
            delayed[M:] = comb_out[:-M]
        comb_out = comb_out - delayed

    if normalize_gain:
        dc_gain = float((R * M) ** N)
        comb_out = comb_out / dc_gain

    return comb_out


def main() -> None:
    N, R, M = 4, 16, 1
    dc_gain = (R * M) ** N

    # 1. Đáp ứng xung đơn vị (Impulse response)
    imp = np.zeros(2000, dtype=np.float64)
    imp[0] = 1.0
    h_dec = cic_decimate_float(imp, N=N, R=R, M=M, normalize_gain=False)

    # Tính đáp ứng xung FIR tương đương ở tốc độ cao fs (độ dài N*(R*M-1)+1 = 61 mẫu)
    h_box = np.ones(R * M, dtype=np.float64)
    h_high_rate = h_box.copy()
    for _ in range(N - 1):
        h_high_rate = np.convolve(h_high_rate, h_box)

    # 2. Đáp ứng bước nhảy (Step response) với tín hiệu hằng số 1.0
    dc_in = np.ones(5000, dtype=np.float64)
    dc_out_raw = cic_decimate_float(dc_in, N=N, R=R, M=M, normalize_gain=False)
    dc_out_norm = dc_out_raw / dc_gain

    print("=== KIỂM TRA FLOATING-POINT MODEL (BƯỚC 1a) ===")
    print(f"Cấu hình           : N={N}, R={R}, M={M}")
    print(f"Số mẫu input       : 5000 -> Số mẫu output: {len(dc_out_raw)}")
    print(f"Độ lợi DC lý thuyết: {dc_gain}")
    print(f"Độ lợi DC xác lập  : {dc_out_raw[-1]:.1f}")
    print(f"Đáp ứng xung (6 mẫu đầu sau decimation): {h_dec[:6]}")

    # 3. Vẽ và lưu đồ thị trực quan
    fig_dir = PROJECT_ROOT / "reports" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig_path = fig_dir / "01_cic_floating_point_response.png"

    fig, axes = plt.subplots(2, 1, figsize=(10, 7.2), dpi=150)

    # Subplot 1: Impulse Response (High-rate vs Decimated samples)
    n_hr = np.arange(len(h_high_rate))
    dec_indices = np.arange(R - 1, len(h_high_rate), R)
    axes[0].plot(n_hr, h_high_rate, color="#1f77b4", linewidth=1.6, label="Đáp ứng xung tốc độ cao (fs = 1 MHz, 61 mẫu)")
    axes[0].stem(
        dec_indices,
        h_high_rate[dec_indices],
        linefmt="r--",
        markerfmt="ro",
        basefmt=" ",
        label="Điểm chốt sau Decimation (n = 16k + 15)",
    )
    for idx in dec_indices:
        axes[0].annotate(
            f"{int(h_high_rate[idx])}",
            (idx, h_high_rate[idx]),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=8.5,
            color="#b22222",
            fontweight="bold",
        )
    axes[0].set_title("Đáp ứng xung đơn vị CIC (N=4, R=16, M=1) & Vị trí trích mẫu giảm tần")
    axes[0].set_xlabel("Chỉ số mẫu đầu vào (n)")
    axes[0].set_ylabel("Biên độ")
    axes[0].set_ylim([0, max(h_high_rate) * 1.18])
    axes[0].grid(True, linestyle=":", alpha=0.7)
    axes[0].legend(loc="upper right")

    # Subplot 2: Step Response (12 mẫu đầu ra đầu tiên)
    k_axis = np.arange(12)
    axes[1].step(k_axis, dc_out_norm[:12], where="mid", color="#2ca02c", linewidth=1.8, marker="o")
    axes[1].axhline(1.0, color="#d62728", linestyle="--", linewidth=1.2, label=f"Mức xác lập chuẩn hóa = 1.0 (DC Gain = {dc_gain})")
    axes[1].set_title("Đáp ứng bước nhảy (Step Response) chuẩn hóa sau Decimation")
    axes[1].set_xlabel("Chỉ số mẫu đầu ra (k)")
    axes[1].set_ylabel("Biên độ chuẩn hóa y[k] / 65536")
    axes[1].set_xticks(k_axis)
    axes[1].set_ylim([-0.05, 1.15])
    axes[1].grid(True, linestyle=":", alpha=0.7)
    axes[1].legend(loc="lower right")

    plt.tight_layout()
    plt.savefig(fig_path, dpi=300, bbox_inches="tight")
    print(f"Đã lưu đồ thị tại: {fig_path}")
    plt.show()


if __name__ == "__main__":
    main()