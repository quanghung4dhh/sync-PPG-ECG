import numpy as np
from scipy.signal import butter, lfilter, lfilter_zi

class RealTimeBandpassFilter:
    def __init__(self, lowcut, highcut, fs, order=5):
        """
        Khởi tạo bộ lọc.
        :param lowcut: Tần số cắt thấp (Hz)
        :param highcut: Tần số cắt cao (Hz)
        :param fs: Tần số lấy mẫu (Hz) - Phải khớp với ESP32
        :param order: Bậc bộ lọc (Mặc định 2 là đủ cho PPG)
        """
        
        #  Tạo hệ số b, a 
        self.b, self.a = butter(order, [lowcut, highcut], btype='band', fs=fs)
        
        # QUAN TRỌNG: Khởi tạo trạng thái 'zi' (Bộ nhớ đệm)
        # Đây là thứ giúp bộ lọc hoạt động liên tục (Real-time)
        self.zi = lfilter_zi(self.b, self.a)
        
    def filter(self, new_sample):
        """
        Lọc một mẫu đơn lẻ.
        :param new_sample: Giá trị thô (float) từ Serial
        :return: Giá trị đã lọc (float)
        """
        # lfilter yêu cầu đầu vào là mảng, nên ta bọc [new_sample]
        # Tham số zi đầu vào là trạng thái cũ, zi đầu ra là trạng thái mới
        filtered_data, self.zi = lfilter(self.b, self.a, [new_sample], zi=self.zi)
        
        return filtered_data[0]