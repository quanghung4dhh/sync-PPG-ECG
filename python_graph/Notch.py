import numpy as np
from scipy import signal

class RealTimeNotchFilter:
    def __init__(self, fs=100.0, freq=50.0, Q=30.0):
        """
        Bộ lọc Notch IIR (Infinite Impulse Response) Real-time.
        Dựa trên: scipy.signal.iirnotch
        
        Tham số:
        - fs (float): Tần số lấy mẫu (Sampling Frequency). 
                      QUAN TRỌNG: Phải khớp với tốc độ gửi của ESP32 (vd: 100Hz).
        - freq (float): Tần số cần cắt bỏ (Frequency to remove).
                      Mặc định 50.0Hz cho điện lưới Việt Nam.
        - Q (float): Hệ số phẩm chất (Quality Factor).
                      Q = Center_Freq / Bandwidth.
                      Q càng cao -> Vết cắt càng hẹp (ít ảnh hưởng tín hiệu xung quanh).
                      Q càng thấp -> Vết cắt càng rộng (cắt nhiễu tốt hơn nhưng dễ méo sóng).
                      Khuyên dùng Q=30.0 cho ECG.
        """
        self.fs = fs
        self.freq = freq
        self.Q = Q
        
        # 1. Tính toán hệ số bộ lọc (b, a) theo tài liệu Scipy
        # Hàm iirnotch trả về tử số (b) và mẫu số (a) của hàm truyền
        self.b, self.a = signal.iirnotch(w0=freq, Q=Q, fs=fs)
        
        # 2. Khởi tạo trạng thái nội tại (zi) cho bộ lọc
        # Đây là "bộ nhớ" của bộ lọc, giúp nó hoạt động liên tục (stream)
        # mà không bị gián đoạn giữa các lần gọi hàm.
        self.zi = signal.lfilter_zi(self.b, self.a)
        
    def process_sample(self, sample_val):
        """
        Lọc từng mẫu đơn lẻ (Sample-by-Sample).
        Dùng cho vòng lặp đọc Serial.
        """
        # lfilter cần đầu vào là list/array, dù chỉ là 1 số
        filtered_val, self.zi = signal.lfilter(self.b, self.a, [sample_val], zi=self.zi)
        return filtered_val[0]

    def apply(self, data_array):
        """
        Lọc cả một mảng dữ liệu (Block processing).
        Dùng nếu bạn muốn lọc lại toàn bộ buffer trước khi vẽ.
        """
        filtered_data, _ = signal.lfilter(self.b, self.a, data_array, zi=self.zi * data_array[0])
        return filtered_data

    def reset(self):
        """Reset trạng thái bộ lọc về ban đầu"""
        self.zi = signal.lfilter_zi(self.b, self.a)