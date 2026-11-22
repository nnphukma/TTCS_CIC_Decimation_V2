"""
generate_sine_stimulus.py
Sinh bộ vector kiểm thử cho Vivado XSim và đánh giá chất lượng phổ sau cắt bit (Bước 1e, 1f):
1. verification/vectors/stimulus.mem & expected.mem:
   Tín hiệu Two-Tone (10 kHz + 200 kHz), 5000 mẫu input -> 312 mẫu output.
2. verification/vectors/stimulus_sine.mem:
   Tín hiệu Coherent Sine (f_in = 37/256 * 62.5 kHz = 9033.203125 Hz, biên độ 1000, 5000 mẫu).
3. Xuất đồ thị báo cáo:
   - reports/figures/04a_two_tone_verification.png
   - reports/figures/04b_coherent_sine_fft.png
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
sys.path.insert(0, str(PYTHON_DIR))

from models.cic_fixed_point import cic_decimate_fixed, int_to_hex, hex_to_int


def write_mem_file(filepath: Path, data: np.ndarray, bits: int) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8", newline="\n") as f:
        for val in data:
            f.write(f"{int_to_hex(int(val), bits)}\n")


def read_mem_file(filepath: Path, bits: int) -> np.ndarray:
    vals = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("//"):
                vals.append(hex_to_int(s, bits))
    return np.array(vals, dtype=np.int64)


def analyze_coherent_fft(
    y_samples: np.ndarray,
    fft_size: int = 256,
    fund_bin: int = 37,
    skip_transient: int = 16,
) -> dict:
    """
    Tính biên độ phổ, SNR, SINAD, SFDR, THD và ENOB trên chuỗi đầu ra xác lập.
    """
    assert len(y_samples) >= skip_transient + fft_size, (
        f"Không đủ mẫu để phân tích FFT (cần >= {skip_transient + fft_size}, có {len(y_samples)})"
    )
    seg = y_samples[skip_transient : skip_transient + fft_size].astype(np.float64)

    spectrum = np.fft.fft(seg)
    mag2 = np.abs(spectrum) ** 2

    fund_amp_lsb = (2.0 * np.abs(spectrum[fund_bin])) / fft_size

    sig_bins = {fund_bin, fft_size - fund_bin}
    p_sig = sum(mag2[b] for b in sig_bins)

    harm_bins = set()
    for h in range(2, 6):
        b = (h * fund_bin) % fft_size
        if b != 0 and b not in sig_bins:
            harm_bins.add(b)
            harm_bins.add(fft_size - b)

    p_dist = sum(mag2[b] for b in harm_bins)

    excluded = {0} | sig_bins | harm_bins
    p_noise = sum(mag2[b] for b in range(1, fft_size) if b not in excluded)

    spur_candidates = [mag2[b] for b in range(1, fft_size) if b not in sig_bins]
    max_spur_power = max(spur_candidates) if spur_candidates else 1e-30

    snr_db = 10.0 * np.log10(max(p_sig, 1e-30) / max(p_noise, 1e-30))
    sinad_db = 10.0 * np.log10(max(p_sig, 1e-30) / max(p_noise + p_dist, 1e-30))
    thd_db = 10.0 * np.log10(max(p_dist, 1e-30) / max(p_sig, 1e-30))
    sfdr_dbc = 10.0 * np.log10(max(p_sig, 1e-30) / max(max_spur_power, 1e-30))
    enob = (sinad_db - 1.76) / 6.02

    # Phổ một phía (0 .. fft_size/2) chuẩn hóa theo đỉnh cơ bản (dBc)
    one_sided_mag = np.abs(spectrum[: fft_size // 2 + 1])
    fund_mag = max(one_sided_mag[fund_bin], 1e-30)
    spec_dbc = 20.0 * np.log10(np.maximum(one_sided_mag / fund_mag, 1e-12))

    return {
        "fund_amp_lsb": fund_amp_lsb,
        "snr_db": snr_db,
        "sinad_db": sinad_db,
        "sfdr_dbc": sfdr_dbc,
        "thd_db": thd_db,
        "enob": enob,
        "spec_dbc": spec_dbc,
    }


def main() -> None:
    N, R, M, W_IN, W_OUT = 4, 16, 1, 12, 12
    fs = 1_000_000.0
    f_out = fs / R
    num_in = 5000
    n = np.arange(num_in, dtype=np.float64)

    vec_dir = PROJECT_ROOT / "verification" / "vectors"
    fig_dir = PROJECT_ROOT / "reports" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # BỘ 1: TWO-TONE INTEGRATION VECTOR (10 kHz + 200 kHz) -> stimulus.mem
    # -------------------------------------------------------------------------
    x_two_tone = np.round(
        1000.0 * np.sin(2.0 * np.pi * 10_000.0 * n / fs)
        + 1000.0 * np.sin(2.0 * np.pi * 200_000.0 * n / fs)
    ).astype(np.int64)
    x_two_tone = np.clip(x_two_tone, -(1 << (W_IN - 1)), (1 << (W_IN - 1)) - 1)

    y_two_tone_exp = cic_decimate_fixed(x_two_tone, N=N, R=R, M=M, w_in=W_IN, w_out=W_OUT)

    write_mem_file(vec_dir / "stimulus.mem", x_two_tone, W_IN)
    write_mem_file(vec_dir / "expected.mem", y_two_tone_exp, W_OUT)

    # -------------------------------------------------------------------------
    # BỘ 2: COHERENT SINE VECTOR (9033.203125 Hz) -> stimulus_sine.mem
    # -------------------------------------------------------------------------
    fft_size = 256
    fund_bin = 37
    f_in_coh = (fund_bin / fft_size) * f_out  # 9033.203125 Hz
    amp_in = 1000.0

    x_sine = np.round(amp_in * np.sin(2.0 * np.pi * f_in_coh * n / fs)).astype(np.int64)
    x_sine = np.clip(x_sine, -(1 << (W_IN - 1)), (1 << (W_IN - 1)) - 1)

    y_sine_exp = cic_decimate_fixed(x_sine, N=N, R=R, M=M, w_in=W_IN, w_out=W_OUT)

    write_mem_file(vec_dir / "stimulus_sine.mem", x_sine, W_IN)

    metrics = analyze_coherent_fft(y_sine_exp, fft_size=fft_size, fund_bin=fund_bin, skip_transient=16)

    print("=== SINH VECTOR & ĐÁNH GIÁ PHỔ COHERENT SINE (BƯỚC 1e & 1f) ===")
    print(f"Đã xuất stimulus.mem      : {len(x_two_tone)} mẫu -> {vec_dir / 'stimulus.mem'}")
    print(f"Đã xuất expected.mem      : {len(y_two_tone_exp)} mẫu -> {vec_dir / 'expected.mem'}")
    print(f"Đã xuất stimulus_sine.mem : {len(x_sine)} mẫu -> {vec_dir / 'stimulus_sine.mem'}")
    print("\n--- Kết quả phân tích Coherent Sine (Golden Fixed-Point 12-bit) ---")
    print(f"  Tần số đầu vào (f_in)   : {f_in_coh:.6f} Hz (Bin {fund_bin}/{fft_size})")
    print(f"  Biên độ cơ bản (FFT)    : {metrics['fund_amp_lsb']:.3f} LSB")
    print(f"  SNR                     : {metrics['snr_db']:.3f} dB")
    print(f"  SINAD                   : {metrics['sinad_db']:.3f} dB")
    print(f"  SFDR                    : {metrics['sfdr_dbc']:.3f} dBc")
    print(f"  THD                     : {metrics['thd_db']:.3f} dB")
    print(f"  ENOB                    : {metrics['enob']:.3f} bits")

    # -------------------------------------------------------------------------
    # ĐỒ THỊ 4A: TWO-TONE INPUT VS GOLDEN EXPECTED OUTPUT
    # -------------------------------------------------------------------------
    fig_4a_path = fig_dir / "04a_two_tone_verification.png"
    fig1, axes1 = plt.subplots(2, 1, figsize=(10.5, 7.0), dpi=150)

    t_in_us = (n[:400] / fs) * 1e6  # 400 us đầu tiên (4 chu kỳ của 10 kHz)
    axes1[0].plot(t_in_us, x_two_tone[:400], color="#7f8c8d", linewidth=1.0)
    axes1[0].set_title("Tín hiệu đầu vào Two-Tone (10 kHz + 200 kHz) tại fs = 1 MHz [stimulus.mem]")
    axes1[0].set_xlabel("Thời gian (µs)")
    axes1[0].set_ylabel("Biên độ 12-bit (LSB)")
    axes1[0].grid(True, linestyle=":", alpha=0.7)

    t_out_us = ((np.arange(25) * R + (R - 1)) / fs) * 1e6  # 25 mẫu đầu ra tương ứng 400 us
    axes1[1].plot(t_out_us, y_two_tone_exp[:25], color="#1f77b4", marker="o", linewidth=1.8)
    axes1[1].set_title("Đầu ra Golden Fixed-Point sau lọc & giảm tần (fs_out = 62.5 kHz) [expected.mem]")
    axes1[1].set_xlabel("Thời gian (µs)")
    axes1[1].set_ylabel("Biên độ 12-bit (LSB)")
    axes1[1].grid(True, linestyle=":", alpha=0.7)

    plt.tight_layout()
    plt.savefig(fig_4a_path, dpi=300, bbox_inches="tight")
    print(f"Đã lưu đồ thị tại: {fig_4a_path}")

    # -------------------------------------------------------------------------
    # ĐỒ THỊ 4B: PHỔ FFT 256 ĐIỂM CỦA COHERENT SINE
    # -------------------------------------------------------------------------
    fig_4b_path = fig_dir / "04b_coherent_sine_fft.png"
    fig2, ax2 = plt.subplots(figsize=(10.5, 5.2), dpi=150)

    freq_bins_khz = np.fft.rfftfreq(fft_size, d=1.0 / f_out) / 1e3
    spec_dbc = metrics["spec_dbc"]

    ax2.plot(freq_bins_khz, spec_dbc, color="#1f77b4", linewidth=1.3)
    ax2.scatter([freq_bins_khz[fund_bin]], [spec_dbc[fund_bin]], color="#d62728", zorder=6, s=50)
    ax2.annotate(
        f"Fundamental (Bin {fund_bin})\n{f_in_coh/1e3:.3f} kHz | {metrics['fund_amp_lsb']:.2f} LSB",
        xy=(freq_bins_khz[fund_bin], spec_dbc[fund_bin]),
        xytext=(freq_bins_khz[fund_bin] + 3.2, -10.0),
        arrowprops=dict(arrowstyle="->", color="#d62728", lw=1.2),
        fontsize=9,
        fontweight="bold",
        color="#900c3f",
    )

    # Hiển thị bảng chỉ số chất lượng phổ ngay trên biểu đồ
    stats_text = (
        f"SNR   : {metrics['snr_db']:.2f} dB\n"
        f"SINAD : {metrics['sinad_db']:.2f} dB\n"
        f"SFDR  : {metrics['sfdr_dbc']:.2f} dBc\n"
        f"THD   : {metrics['thd_db']:.2f} dB\n"
        f"ENOB  : {metrics['enob']:.2f} bits"
    )
    ax2.text(
        0.98,
        0.95,
        stats_text,
        transform=ax2.transAxes,
        fontsize=9.5,
        verticalalignment="top",
        horizontalalignment="right",
        family="monospace",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#f8f9f9", edgecolor="#aeb6bf", alpha=0.95),
    )

    ax2.set_title("Phổ FFT 256 điểm đầu ra Coherent Sine (Golden Fixed-Point 12-bit)")
    ax2.set_xlabel("Tần số (kHz) [Nyquist = 31.25 kHz]")
    ax2.set_ylabel("Biên độ tương đối (dBc)")
    ax2.set_xlim([0, 31.25])
    ax2.set_ylim([-125, 10])
    ax2.grid(True, which="both", linestyle=":", alpha=0.7)

    plt.tight_layout()
    plt.savefig(fig_4b_path, dpi=300, bbox_inches="tight")
    print(f"Đã lưu đồ thị tại: {fig_4b_path}")
    plt.show()


if __name__ == "__main__":
    main()