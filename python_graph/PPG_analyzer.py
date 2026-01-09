import numpy as np
from scipy.signal import find_peaks


class PPGAnalyzer:
    def __init__(self, fs=50, spo2_cal_coeffs=(110, 25)):
        """
        Khởi tạo bộ phân tích PPG.

        Tham số:
        - fs (int): Tần số lấy mẫu (Sampling rate) tính bằng Hz. Mặc định là 100Hz.
        - spo2_cal_coeffs (tuple): Hệ số hiệu chuẩn (A, B) cho công thức SpO2 = A - B * R.
                                   Mặc định là (110, 25).
        """
        self.fs = fs
        self.A, self.B = spo2_cal_coeffs

    def update_fs(self, new_fs):
        """Cập nhật tần số lấy mẫu nếu thay đổi."""
        self.fs = new_fs

    def _calculate_r_ratio(self, ac_red, dc_red, ac_ir, dc_ir):
        """Tính tỷ lệ R = (AC_red/DC_red) / (AC_ir/DC_ir)"""
        # Tránh chia cho 0
        if dc_red == 0 or dc_ir == 0 or ac_ir == 0:
            return 0

        r = (ac_red / dc_red) / (ac_ir / dc_ir)
        return r

    def analyze(self, red_signal, ir_signal):
        """
        Phân tích tín hiệu để trả về BPM và SpO2.

        Tham số:
        - red_signal (array-like): Mảng tín hiệu Đỏ (đã lọc).
        - ir_signal (array-like): Mảng tín hiệu Hồng ngoại (đã lọc).

        Trả về:
        - dict: {'bpm': float, 'spo2': float, 'status': str}
        """
        # Chuyển đổi sang numpy array để dễ xử lý
        red = np.array(red_signal)
        ir = np.array(ir_signal)

        # Kiểm tra độ dài dữ liệu
        if len(red) != len(ir):
            return {'bpm': None, 'spo2': None, 'status': "Error: Signal lengths mismatch"}

        if len(ir) < self.fs:  # Cần ít nhất 1 giây dữ liệu
            return {'bpm': None, 'spo2': None, 'status': "Error: Not enough data"}

        # --- TÍNH BPM (Dựa trên IR) ---
        # distance=self.fs/2.5 tương đương giới hạn nhịp tim tối đa ~150 BPM để tránh nhiễu
        peaks, _ = find_peaks(ir, distance=self.fs/2.5)

        bpm = 0
        if len(peaks) >= 2:
            peak_intervals = np.diff(peaks)
            mean_interval_sec = np.mean(peak_intervals) / self.fs
            bpm = 60 / mean_interval_sec
        else:
            return {'bpm': None, 'spo2': None, 'status': "Warning: Cannot detect peaks"}

        # --- TÍNH SpO2 ---
        # Tính AC và DC cho toàn bộ cửa sổ tín hiệu
        # DC = Giá trị trung bình
        dc_red = np.mean(red)
        dc_ir = np.mean(ir)

        # AC = Peak-to-Peak (Max - Min)
        ac_red = np.max(red) - np.min(red)
        ac_ir = np.max(ir) - np.min(ir)

        # Tính tỷ lệ R
        R = self._calculate_r_ratio(ac_red, dc_red, ac_ir, dc_ir)

        # Tính SpO2 theo công thức tuyến tính: SpO2 = A - B * R
        spo2 = self.A - (self.B * R)

        # Giới hạn SpO2 trong khoảng hợp lý (0-100%)
        spo2 = np.clip(spo2, 0, 100)

        return {
            'bpm': round(bpm, 2),
            'spo2': round(spo2, 2),
            'status': "Success"
        }
