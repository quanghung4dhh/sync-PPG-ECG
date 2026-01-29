import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import threading
from Notch import RealTimeNotchFilter
from BandPass_filter import RealTimeBandpassFilter
from SGS import RealTimeSmoother

# --- CẤU HÌNH ---
SERIAL_PORT = 'COM3' 
BAUD_RATE = 921600

# Số lượng điểm dữ liệu hiển thị trên màn hình (cửa sổ trượt)
MAX_DATA_POINTS = 500 

# --- KHỞI TẠO DỮ LIỆU ---
# Deque là một danh sách hàng đợi, tự động đẩy dữ liệu cũ ra khi đầy
# Giúp tạo hiệu ứng cuộn (scrolling)
data_buffer = deque([0] * MAX_DATA_POINTS, maxlen=MAX_DATA_POINTS)

# Khởi tạo bộ lọc
bandpassFilterECG = RealTimeBandpassFilter(
        lowcut=0.5, highcut=40, fs=100, order=2)
notch_filter = RealTimeNotchFilter(fs=100.0, freq=50.0, Q=30.0)

# Khởi tạo bộ làm mượt
smoother = RealTimeSmoother(window_length=9, polyorder=2, mode='mirror')

# Biến cờ để kiểm soát luồng đọc dữ liệu
is_running = True

# --- THIẾT LẬP KẾT NỐI SERIAL ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"Đã kết nối thành công tới {SERIAL_PORT}")
    # Xóa bộ đệm ban đầu để tránh dữ liệu rác
    ser.reset_input_buffer()
except serial.SerialException:
    print(f"LỖI: Không thể mở cổng {SERIAL_PORT}. Hãy kiểm tra lại dây cáp hoặc tắt Serial Monitor khác.")
    exit()

# --- HÀM ĐỌC DỮ LIỆU (Chạy luồng riêng) ---
def read_serial_data():
    global is_running
    while is_running:
        try:
            # Đọc một dòng dữ liệu từ ESP32
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if not line or ',' not in line: continue
            parts = line.split(',')
            
            # Chỉ xử lý nếu dòng có dữ liệu
            if len(parts) >= 3:
                try:
                    # Chuyển đổi sang số nguyên (0-4095)
                    val = int(parts[0])

                    #Notch
                    notch_val = notch_filter.process_sample(val)

                    #Bandpass
                    filtered_ecg = bandpassFilterECG.filter(notch_val)
                    
                    # Thêm vào hàng đợi (dữ liệu cũ nhất sẽ tự mất)
                    data_buffer.append(2*filtered_ecg)
                    
                except ValueError:
                    # Bỏ qua nếu nhận được ký tự lạ (ví dụ '!' khi tuột dây)
                    pass
        except Exception as e:
            print(f"Lỗi đọc Serial: {e}")
            break

# --- HÀM CẬP NHẬT ĐỒ THỊ ---
def update_plot(frame):
    current_data = list(data_buffer)
    smoothed_data = smoother.apply(current_data)
    line.set_ydata(smoothed_data)
    return line,

# --- THIẾT LẬP ĐỒ THỊ MATPLOTLIB ---
fig, ax = plt.subplots()
ax.set_title(f'Raw ECG')
ax.set_xlabel('Sample')
ax.set_ylabel('ADC Value')

# Cố định trục Y từ 0 đến 4095 (độ phân giải ESP32)
# Bạn có thể thu hẹp lại (vd: 1000 - 3000) để nhìn sóng rõ hơn nếu cần
ax.set_ylim(-4095, 4095) 
ax.set_xlim(0, MAX_DATA_POINTS)
ax.grid(True, linestyle='--', alpha=0.5)

# Tạo đường vẽ
line, = ax.plot(list(range(MAX_DATA_POINTS)), data_buffer, color='red', linewidth=1.2)

# Bắt đầu luồng đọc dữ liệu nền
thread = threading.Thread(target=read_serial_data)
thread.daemon = True # Tự tắt khi chương trình chính tắt
thread.start()

# Bắt đầu Animation
# interval=20ms nghĩa là vẽ lại màn hình 50 lần/giây
ani = animation.FuncAnimation(fig, update_plot, interval=20, blit=True, cache_frame_data=False)

print("Đang vẽ đồ thị... Nhấn đóng cửa sổ để thoát.")
plt.show()

# Khi tắt cửa sổ đồ thị, dọn dẹp kết nối
is_running = False
ser.close()
print("Đã ngắt kết nối.")