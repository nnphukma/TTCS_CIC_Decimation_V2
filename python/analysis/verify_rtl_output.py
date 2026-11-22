"""
verify_rtl_output.py
Kiểm chứng toàn diện kết quả mô phỏng RTL (Bước 4b & 4c):
1. Thu thập rtl_output.mem & rtl_sine_output.mem từ thư mục XSim về verification/results/.
2. Đối chiếu bit-exact 312/312 mẫu giữa rtl_output.mem và expected.mem.
3. Đo mức triệt tiêu nhiễu alias 200 kHz -> 12.5 kHz trên tín hiệu Two-Tone (250-pt FFT).
4. Phân tích phổ FFT 256 điểm trên rtl_sine_output.mem (SNR, SINAD, SFDR, THD, ENOB).
5. Xuất đồ thị báo cáo: reports/figures/05_rtl_verification_spectrum.png
"""

import shutil
import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
sys.path.insert(0, str(PYTHON_DIR))

from generators.generate_sine_stimulus import read_mem_file, analyze_coherent_fft


def fetch_latest_xsim_file(sim_root: Path, filename: str, dest_dir: Path) -> Path:
    matches = list(sim_root.rglob(filename))
    if not matches:
        raise FileNotFoundError(
            f"Không tìm thấy '{filename}' trong {sim_root}. Hãy chạy simulation trong Vivado trước."
        )
    latest_file = max(matches, key=lambda p: p.stat().st_mtime)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename
    shutil.copy2(latest_file, dest_path)
    print(f"Đã thu thập {filename} từ: {latest_file.relative_to(PROJECT_ROOT)}")
    return dest_path


def main() -> None:
    W_OUT = 12
    fs = 1_000_000.0
    N, R, M = 4, 16, 1
    f_out = fs / R  # 62.5 kHz

    sim_dir = PROJECT_ROOT / "CIC_DecimationV2.sim"
    vec_dir = PROJECT_ROOT / "verification" / "vectors"
    res_dir = PROJECT_ROOT / "verification" / "results"
    fig_dir = PROJECT_ROOT / "reports" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    print("=== KIỂM CHỨNG BIT-EXACT & ĐẶC TÍNH PHỔ RTL (BƯỚC 4b & 4c) ===")

    # -------------------------------------------------------------------------
    # 1. Đối chiếu Bit-Exact 312/312 mẫu (Two-Tone)
    # -------------------------------------------------------------------------
    rtl_out_path = fetch_latest_xsim_file(sim_dir, "rtl_output.mem", res_dir)
    exp_out_path = vec_dir / "expected.mem"

    y_rtl = read_mem_file(rtl_out_path, W_OUT)
    y_exp = read_mem_file(exp_out_path, W_OUT)

    assert len(y_rtl) == len(y_exp) == 312, (
        f"Sai số lượng mẫu: RTL = {len(y_rtl)}, Expected = {len(y_exp)}"
    )
    mismatches = np.where(y_rtl != y_exp)[0]
    if len(mismatches) > 0:
        idx0 = mismatches[0]
        raise AssertionError(
            f"FAIL: Phát hiện {len(mismatches)} mẫu sai lệch! Đầu tiên tại index {idx0}: "
            f"Expected={y_exp[idx0]}, RTL={y_rtl[idx0]}"
        )
    print(f"[PASS] Bit-exact Two-Tone Verification: {len(y_rtl)}/312 mẫu khớp tuyệt đối (0 sai lệch).")

    # Phân tích phổ Two-Tone bằng FFT 250 điểm (df = 62.5 kHz / 250 = 250 Hz)
    # 10 kHz -> Bin 40 (chính xác); 200 kHz alias về 12.5 kHz -> Bin 50 (chính xác)
    n_fft_tt = 250
    seg_tt = y_rtl[16 : 16 + n_fft_tt].astype(np.float64)
    spec_tt = np.fft.rfft(seg_tt)
    amp_tt_lsb = (2.0 * np.abs(spec_tt)) / n_fft_tt
    freq_tt_khz = np.fft.rfftfreq(n_fft_tt, d=1.0 / f_out) / 1e3

    amp_10k_lsb = amp_tt_lsb[40]
    amp_alias_12k5_lsb = amp_tt_lsb[50]
    h_10k_theory = (np.sin(np.pi * R * M * 10e3 / fs) / (R * M * np.sin(np.pi * 10e3 / fs))) ** N
    amp_10k_theory = 1000.0 * abs(h_10k_theory)
    atten_alias_db = 20.0 * np.log10(max(amp_alias_12k5_lsb, 1e-12) / 1000.0)

    print("\n--- Phân tích Triệt tiêu Alias Two-Tone trên RTL (10 kHz + 200 kHz) ---")
    print(f"  Biên độ 10 kHz (Passband)     : {amp_10k_lsb:.3f} LSB (Lý thuyết: {amp_10k_theory:.3f} LSB)")
    print(f"  Biên độ 200 kHz (Alias 12.5k) : {amp_alias_12k5_lsb:.4f} LSB (< 1 LSB quantization floor)")
    print(f"  Suy hao thực tế tại 200 kHz   : {atten_alias_db:.2f} dB (Lý thuyết: -96.33 dB)")

    # -------------------------------------------------------------------------
    # 2. Phân tích Phổ Coherent Sine RTL (256-pt FFT, Bin 37)
    # -------------------------------------------------------------------------
    fft_size = 256
    fund_bin = 37
    f_in_coh = (fund_bin / fft_size) * f_out

    rtl_sine_path = fetch_latest_xsim_file(sim_dir, "rtl_sine_output.mem", res_dir)
    y_rtl_sine = read_mem_file(rtl_sine_path, W_OUT)
    assert len(y_rtl_sine) == 312, f"Sai số lượng mẫu sine: RTL = {len(y_rtl_sine)}"

    metrics = analyze_coherent_fft(y_rtl_sine, fft_size=fft_size, fund_bin=fund_bin, skip_transient=16)

    print("\n--- Phân tích Phổ Coherent Sine trên RTL (9033.203125 Hz) ---")
    print(f"  Biên độ cơ bản (FFT) : {metrics['fund_amp_lsb']:.3f} LSB")
    print(f"  SNR                  : {metrics['snr_db']:.3f} dB")
    print(f"  SINAD                : {metrics['sinad_db']:.3f} dB")
    print(f"  SFDR                 : {metrics['sfdr_dbc']:.3f} dBc")
    print(f"  THD                  : {metrics['thd_db']:.3f} dB")
    print(f"  ENOB                 : {metrics['enob']:.3f} bits")

    # -------------------------------------------------------------------------
    # 3. Xuất đồ thị báo cáo tổng hợp Bước 4c
    # -------------------------------------------------------------------------
    fig_path = fig_dir / "05_rtl_verification_spectrum.png"
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 7.8), dpi=150)

    # Subplot 1: Phổ Coherent Sine RTL (dBc)
    freq_bins_khz = np.fft.rfftfreq(fft_size, d=1.0 / f_out) / 1e3
    spec_dbc = metrics["spec_dbc"]
    axes[0].plot(freq_bins_khz, spec_dbc, color="#1f77b4", linewidth=1.3)
    axes[0].scatter([freq_bins_khz[fund_bin]], [spec_dbc[fund_bin]], color="#d62728", zorder=6, s=50)
    axes[0].annotate(
        f"RTL Fundamental (Bin {fund_bin})\n{f_in_coh/1e3:.3f} kHz | {metrics['fund_amp_lsb']:.2f} LSB",
        xy=(freq_bins_khz[fund_bin], spec_dbc[fund_bin]),
        xytext=(freq_bins_khz[fund_bin] + 3.2, -12.0),
        arrowprops=dict(arrowstyle="->", color="#d62728", lw=1.2),
        fontsize=9,
        fontweight="bold",
        color="#900c3f",
    )
    stats_text = (
        f"RTL COHERENT SINE\n"
        f"SNR   : {metrics['snr_db']:.2f} dB\n"
        f"SINAD : {metrics['sinad_db']:.2f} dB\n"
        f"SFDR  : {metrics['sfdr_dbc']:.2f} dBc\n"
        f"THD   : {metrics['thd_db']:.2f} dB\n"
        f"ENOB  : {metrics['enob']:.2f} bits"
    )
    axes[0].text(
        0.98, 0.94, stats_text, transform=axes[0].transAxes, fontsize=9,
        verticalalignment="top", horizontalalignment="right", family="monospace",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#f8f9f9", edgecolor="#aeb6bf", alpha=0.95),
    )
    axes[0].set_title("Phổ FFT 256 điểm đầu ra RTL Option B – Coherent Sine (9.033 kHz)")
    axes[0].set_xlabel("Tần số (kHz)")
    axes[0].set_ylabel("Biên độ tương đối (dBc)")
    axes[0].set_xlim([0, 31.25])
    axes[0].set_ylim([-125, 10])
    axes[0].grid(True, which="both", linestyle=":", alpha=0.7)

    # Subplot 2: Phổ Two-Tone RTL (250-pt FFT, biên độ dBFS)
    spec_tt_dbfs = 20.0 * np.log10(np.maximum(amp_tt_lsb / 2048.0, 1e-12))
    axes[1].plot(freq_tt_khz[1:], spec_tt_dbfs[1:], color="#2ca02c", linewidth=1.3)
    axes[1].scatter([10.0, 12.5], [spec_tt_dbfs[40], spec_tt_dbfs[50]], color=["#d62728", "#9467bd"], zorder=6, s=45)
    axes[1].annotate(
        f"Tín hiệu giữ lại: 10 kHz\n({amp_10k_lsb:.2f} LSB)",
        xy=(10.0, spec_tt_dbfs[40]),
        xytext=(2.5, -18.0),
        arrowprops=dict(arrowstyle="->", color="#d62728", lw=1.2),
        fontsize=8.5, fontweight="bold", color="#900c3f",
    )
    axes[1].annotate(
        f"Nhiễu 200 kHz alias về 12.5 kHz\n({amp_alias_12k5_lsb:.4f} LSB | {atten_alias_db:.1f} dB)",
        xy=(12.5, spec_tt_dbfs[50]),
        xytext=(15.5, -62.0),
        arrowprops=dict(arrowstyle="->", color="#9467bd", lw=1.2),
        fontsize=8.5, fontweight="bold", color="#5b2c6f",
    )
    axes[1].set_title("Phổ FFT 250 điểm đầu ra RTL Option B – Kiểm chứng triệt tiêu Alias Two-Tone")
    axes[1].set_xlabel("Tần số (kHz)")
    axes[1].set_ylabel("Biên độ (dBFS)")
    axes[1].set_xlim([0, 31.25])
    axes[1].set_ylim([-125, 5])
    axes[1].grid(True, which="both", linestyle=":", alpha=0.7)

    plt.tight_layout()
    plt.savefig(fig_path, dpi=300, bbox_inches="tight")
    print(f"\nĐã lưu đồ thị báo cáo RTL tại: {fig_path}")
    plt.show()


if __name__ == "__main__":
    main()