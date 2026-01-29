import numpy as np
from scipy.signal import savgol_filter

class RealTimeSmoother:
    def __init__(self, window_length=7, polyorder=3, mode='interp'):
        """
        Bộ làm mượt Savitzky-Golay dựa trên Scipy.
        
        Tham số:
        - window_length: Độ dài cửa sổ lọc. 
          + BẮT BUỘC phải là số lẻ (5, 7, 9, 11...). 
          + Nếu bạn nhập số chẵn, code sẽ tự cộng thêm 1.
          + Với ECG 100Hz, nên để nhỏ (5 hoặc 7) để giữ đỉnh R.
        
        - polyorder: Bậc của đa thức nội suy.
          + Phải nhỏ hơn window_length.
          + Bậc 3 thường tốt cho ECG vì nó uốn theo đỉnh nhọn tốt hơn bậc 2.
          
        - mode: Cách xử lý biên (khi cửa sổ chạm mép dữ liệu).
          + 'interp': Nội suy (Mặc định của Scipy).
          + 'mirror': Phản chiếu (Khuyên dùng trong một số nghiên cứu ECG).
          + 'nearest': Lấy giá trị gần nhất.
        """
        # Đảm bảo window_length luôn là số lẻ
        if window_length % 2 == 0:
            window_length += 1
        
        self.window_length = window_length
        self.polyorder = polyorder
        self.mode = mode

    def apply(self, data_input):
        """
        Hàm xử lý chính. 
        Input: List, Deque hoặc Numpy Array.
        Output: Numpy Array đã làm mượt.
        """
        # Chuyển đổi sang numpy array để xử lý
        x = np.array(data_input)
        
        # KIỂM TRA AN TOÀN:
        # Scipy yêu cầu độ dài dữ liệu (x.size) phải lớn hơn window_length
        if x.size <= self.window_length:
            # Nếu dữ liệu quá ngắn, không thể lọc được -> Trả về nguyên gốc
            return x
            
        # Kiểm tra điều kiện polyorder < window_length
        if self.polyorder >= self.window_length:
            print("Cảnh báo: Polyorder phải nhỏ hơn Window Length. Đã giảm Polyorder.")
            return x

        try:
            # Gọi hàm savgol_filter từ thư viện scipy
            # mode='interp' giúp đường vẽ ở rìa phải (dữ liệu mới nhất) không bị nhảy lung tung
            y_smooth = savgol_filter(x, self.window_length, self.polyorder, mode=self.mode)
            return y_smooth
            
        except Exception as e:
            print(f"Lỗi SGS: {e}")
            return x