"""
cic_frequency_response.py
Phân tích đáp ứng tần số lý thuyết & thực nghiệm của bộ lọc CIC (Bước 1b, 1c):
- Sử dụng thuần NumPy và Matplotlib.
- Vẽ biểu đồ phổ biên độ toàn dải [0, Fs/2] và dải thông [0, Fs_out/2].
- Xác nhận vị trí các điểm null tại k * Fs_out / M.
- Xác nhận độ lợi DC (R*M)^N, passband droop và stopband attenuation.
Xuất đồ thị: reports/figures/03_cic_frequency_response.png
"""

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def cic_analytical_mag(f_hz: np.ndarray, fs: float, N: int = 4, R: int = 16, M: int = 1) -> np.ndarray:
    """Tính đáp ứng biên độ chuẩn hóa |H(f)| của bộ lọc CIC bậc N."""
    f = np.asarray(f_hz, dtype=np.float64)
    mag = np.ones_like(f)
    non_zero = f > 0.0
    num = np.sin(np.pi * R * M * f[non_zero] / fs)
    den = R * M * np.sin(np.pi * f[non_zero] / fs)
    mag[non_zero] = np.abs(num / den) ** N
    return mag


def main() -> None:
    N, R, M = 4, 16, 1
    fs = 1_000_000.0
    f_out = fs / R
    f_nyq_out = f_out / 2.0

    n_fft = 40000
    f_axis = np.fft.rfftfreq(n_fft, d=1.0 / fs)
    mag_norm = cic_analytical_mag(f_axis, fs, N=N, R=R, M=M)
    mag_db = 20.0 * np.log10(np.maximum(mag_norm, 1e-15))

    # Đối chiếu với FFT của đáp ứng xung FIR tương đương
    h_box = np.ones(R * M, dtype=np.float64) / (R * M)
    h_cic = h_box.copy()
    for _ in range(N - 1):
        h_cic = np.convolve(h_cic, h_box)
    h_fft = np.fft.rfft(h_cic, n=n_fft)
    fft_db = 20.0 * np.log10(np.maximum(np.abs(h_fft), 1e-15))

    print("=== PHÂN TÍCH ĐÁP ỨNG TẦN SỐ CIC (BƯỚC 1b & 1c) ===")
    print(f"Độ lợi DC lý thuyết (R*M)^N : {(R * M) ** N} ({20*np.log10((R*M)**N):.4f} dB)")

    print("\n--- Bảng Passband Droop (Dải thông 0 -> 31.25 kHz) ---")
    test_freqs = [0.0, 5_000.0, 10_000.0, 15_000.0, 20_000.0, 25_000.0, 31_250.0]
    droops = 20.0 * np.log10(cic_analytical_mag(np.array(test_freqs), fs, N=N, R=R, M=M))
    for f_val, d_val in zip(test_freqs, droops):
        print(f"  f = {f_val/1e3:6.2f} kHz  ->  Gain = {d_val:8.4f} dB")

    print("\n--- Kiểm tra vị trí các điểm Null (k * Fs_out / M) ---")
    null_freqs = [k * f_out / M for k in range(1, 9)]
    null_mags = cic_analytical_mag(np.array(null_freqs), fs, N=N, R=R, M=M)
    for k, (fn, mn) in enumerate(zip(null_freqs, null_mags), start=1):
        print(f"  Null k={k}: f = {fn/1e3:6.2f} kHz  ->  |H(f)| = {mn:.2e}")

    atten_200k = 20.0 * np.log10(cic_analytical_mag(np.array([200_000.0]), fs, N=N, R=R, M=M)[0])
    print(f"\nSuy hao Stopband tại 200 kHz : {atten_200k:.4f} dB")

    # Xuất hình ảnh chất lượng cao vào reports/figures/03_cic_frequency_response.png
    fig_dir = PROJECT_ROOT / "reports" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig_path = fig_dir / "03_cic_frequency_response.png"

    fig, axes = plt.subplots(2, 1, figsize=(10.5, 7.8), dpi=150)

    # Subplot 1: Toàn dải [0, 500 kHz]
    axes[0].plot(f_axis / 1e3, mag_db, color="#1f77b4", linewidth=1.5, label="Đáp ứng chuẩn hóa CIC (N=4, R=16, M=1)")
    for k, fn in enumerate(null_freqs):
        axes[0].axvline(
            fn / 1e3,
            color="#d62728",
            linestyle="--",
            alpha=0.45,
            label="Điểm Null (k × 62.5 kHz)" if k == 0 else "",
        )
    axes[0].scatter([200.0], [atten_200k], color="#9467bd", zorder=6, s=45)
    axes[0].annotate(
        f"200 kHz: {atten_200k:.2f} dB",
        xy=(200.0, atten_200k),
        xytext=(225.0, atten_200k + 16.0),
        arrowprops=dict(arrowstyle="->", color="#9467bd", lw=1.2),
        fontsize=9,
        fontweight="bold",
        color="#5b2c6f",
    )
    axes[0].set_title("Đáp ứng biên độ chuẩn hóa CIC Decimation (Toàn dải 0 – 500 kHz)")
    axes[0].set_xlabel("Tần số (kHz)")
    axes[0].set_ylabel("Biên độ (dB)")
    axes[0].set_ylim([-140, 8])
    axes[0].set_xlim([0, 500])
    axes[0].grid(True, which="both", linestyle=":", alpha=0.7)
    axes[0].legend(loc="upper right")

    # Subplot 2: Zoom dải thông [0, 31.25 kHz]
    pb_mask = f_axis <= f_nyq_out
    axes[1].plot(f_axis[pb_mask] / 1e3, mag_db[pb_mask], color="#2ca02c", linewidth=1.8)
    axes[1].scatter(np.array(test_freqs) / 1e3, droops, color="#d62728", zorder=5, s=40)
    for f_val, d_val in zip(test_freqs, droops):
        offset_y = -13 if f_val < 25_000 else 6
        offset_x = 12 if f_val == 0 else (-18 if f_val == 31_250 else 0)
        axes[1].annotate(
            f"{d_val:.2f} dB",
            (f_val / 1e3, d_val),
            textcoords="offset points",
            xytext=(offset_x, offset_y),
            ha="center",
            fontsize=8.5,
            color="#900c3f",
            fontweight="bold",
        )
    axes[1].set_title("Passband Droop trong dải Nyquist đầu ra (0 – 31.25 kHz)")
    axes[1].set_xlabel("Tần số (kHz)")
    axes[1].set_ylabel("Suy hao dải thông (dB)")
    axes[1].set_xlim([-0.5, 32.5])
    axes[1].set_ylim([-18, 2])
    axes[1].grid(True, which="both", linestyle=":", alpha=0.7)

    plt.tight_layout()
    plt.savefig(fig_path, dpi=300, bbox_inches="tight")
    print(f"\nĐã lưu đồ thị tại: {fig_path}")
    plt.show()


if __name__ == "__main__":
    main()