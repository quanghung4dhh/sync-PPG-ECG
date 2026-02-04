import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import time
import threading
import matplotlib.ticker as ticker

# Định nghĩa hàm đổi từ Số mẫu (Index) -> Giây (Seconds)
def sample_to_seconds(x, pos):
    # x là vị trí mẫu (vd: 100), trả về chuỗi (vd: "1s")
    # FS = 100 là tần số lấy mẫu của bạn
    return f"{int(x / 100)}"

# --- IMPORT CÁC MODULE XỬ LÝ (Đảm bảo các file này nằm cùng thư mục) ---
try:
    from Notch import RealTimeNotchFilter
    from BandPass_filter import RealTimeBandpassFilter
    from SGS import RealTimeSmoother
    from PPG_analyzer import PPGAnalyzer
except ImportError as e:
    print(f"LỖI THIẾU THƯ VIỆN: {e}")
    print("Vui lòng đảm bảo các file Notch.py, BandPass_filter.py, SGS.py, PPG_analyzer.py nằm cùng thư mục.")
    exit()

# --- CẤU HÌNH ---
SERIAL_PORT = 'COM3'     # Thay đổi cổng COM cho phù hợp
BAUD_RATE = 921600       # Khuyến nghị tốc độ cao cho 4 trường dữ liệu @ 100Hz
WINDOW_SIZE = 500        # Số điểm hiển thị (500 điểm @ 100Hz = 5 giây)
FS = 100                 # Tần số lấy mẫu (Hz)

# --- KHỞI TẠO BỘ LỌC ---
# 1. Bộ lọc cho ECG (Lọc nhiễu nguồn 50Hz + Lọc thông dải 0.5-40Hz + Làm mượt)
notch_filter_ecg = RealTimeNotchFilter(fs=FS, freq=50.0, Q=30.0)
bandpass_filter_ecg = RealTimeBandpassFilter(lowcut=0.5, highcut=40.0, fs=FS, order=2)
smoother_ecg = RealTimeSmoother(window_length=9, polyorder=2, mode='mirror')

# 2. Bộ lọc cho PPG (Lọc thông dải 0.5-12Hz cho sóng mạch)
# Lưu ý: RED và IR cần bộ lọc riêng biệt
bandpass_filter_red = RealTimeBandpassFilter(lowcut=0.5, highcut=12.0, fs=FS, order=2)
bandpass_filter_ir = RealTimeBandpassFilter(lowcut=0.5, highcut=12.0, fs=FS, order=2)

# 3. Bộ phân tích SpO2/BPM
analyzer = PPGAnalyzer(fs=FS, spo2_cal_coeffs=(110, 25))

# --- KHỞI TẠO KẾT NỐI SERIAL ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    print(f"-> Đã kết nối tới {SERIAL_PORT} @ {BAUD_RATE} baud.")
    time.sleep(2) # Đợi nạp điện
    ser.reset_input_buffer()
except serial.SerialException:
    print(f"LỖI: Không thể mở cổng {SERIAL_PORT}.")
    exit()

# --- KHỞI TẠO DỮ LIỆU ---
# Deque để vẽ đồ thị (Dữ liệu đã lọc)
time_data = deque([0]*WINDOW_SIZE, maxlen=WINDOW_SIZE) # Nếu muốn dùng trục thời gian thực
ecg_data = deque([0]*WINDOW_SIZE, maxlen=WINDOW_SIZE)
red_data = deque([0]*WINDOW_SIZE, maxlen=WINDOW_SIZE)
ir_data = deque([0]*WINDOW_SIZE, maxlen=WINDOW_SIZE)

# Deque dữ liệu thô để tính toán SpO2 (cần giữ nguyên giá trị DC)
raw_red_buffer = deque([0]*WINDOW_SIZE, maxlen=WINDOW_SIZE)
raw_ir_buffer = deque([0]*WINDOW_SIZE, maxlen=WINDOW_SIZE)

# --- THIẾT LẬP ĐỒ THỊ ---
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
plt.subplots_adjust(hspace=0.3)
fig.canvas.manager.set_window_title(f'Vital Signs Monitor - {SERIAL_PORT}')

# 1. Đồ thị ECG
line_ecg, = ax1.plot(ecg_data, color='green', linewidth=1.2, label='ECG Filtered')
ax1.set_ylabel('ECG (mV)')
ax1.set_title("ECG", fontweight='bold')
ax1.grid(True, linestyle=':', alpha=0.6)
ax1.set_ylim(-3000, 3000) # Cố định trục Y ban đầu

# 2. Đồ thị RED (PPG)
line_red, = ax2.plot(red_data, color='red', linewidth=1.5, label='PPG Red')
ax2.set_ylabel('Amplitude')
ax2.set_title("PPG Red", fontweight='bold')
ax2.grid(True, linestyle=':', alpha=0.6)
ax2.set_ylim(-3000, 3000)

# 3. Đồ thị IR (PPG)
line_ir, = ax3.plot(ir_data, color='blue', linewidth=1.5, label='PPG IR')
ax3.set_ylabel('Amplitude')
ax3.set_xlabel('Time (seconds)')
time_axis = [i / FS for i in range(WINDOW_SIZE)] # Chuyển thành s
ax3.xaxis.set_major_formatter(ticker.FuncFormatter(sample_to_seconds))
# Tiêu đề của biểu đồ IR sẽ dùng để hiển thị kết quả SpO2
title_spo2 = ax3.set_title("PPG IR - Waiting for analysis...", fontweight='bold', color='gray')
ax3.grid(True, linestyle=':', alpha=0.6)
ax3.set_ylim(-5000, 5000)

# --- HÀM CẬP NHẬT ---
frame_counter = 0

def update(frame):
    global frame_counter
    
    # Đọc hết dữ liệu trong bộ đệm để tránh lag (Anti-lag loop)
    while ser.in_waiting:
        try:
            # Đọc dòng: "micro, ecg, ir, red"
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if not line or ',' not in line: continue
            
            parts = line.split(',')
            
            # Kiểm tra đủ 3 thành phần
            if len(parts) >= 3:
                # 1. Parse dữ liệu
                # timestamp = float(parts[0]) # Chưa dùng để vẽ, nhưng có thể lưu log
                raw_ecg = float(parts[0])
                raw_ir = float(parts[1])
                raw_red = float(parts[2])
                
                # 2. Xử lý ECG
                # Notch -> Bandpass
                ecg_notch = notch_filter_ecg.process_sample(raw_ecg)
                ecg_filtered = bandpass_filter_ecg.filter(ecg_notch)
                # Lưu vào deque (nhân 2 để tăng biên độ hiển thị nếu cần)
                ecg_data.append(ecg_filtered * 2) 

                # 3. Xử lý PPG (Red & IR)
                # Lưu dữ liệu thô cho thuật toán SpO2
                raw_red_buffer.append(raw_red)
                raw_ir_buffer.append(raw_ir)

                # Lọc Bandpass để vẽ đồ thị (loại bỏ thành phần DC)
                # Đảo dấu (-) vì tín hiệu hấp thụ quang học thường ngược pha với mạch đập
                red_filtered = -bandpass_filter_red.filter(raw_red)
                ir_filtered = -bandpass_filter_ir.filter(raw_ir)
                
                red_data.append(red_filtered)
                ir_data.append(ir_filtered)
                
        except ValueError:
            pass # Bỏ qua lỗi chuyển đổi số
        except Exception as e:
            print(f"Error: {e}")

    # Cập nhật đường vẽ (chỉ cần set lại dữ liệu Y, trục X tự động là index)
    # Áp dụng bộ làm mượt cho ECG (Smoother) trên toàn bộ cửa sổ hiển thị để đẹp hơn
    smoothed_ecg = smoother_ecg.apply(list(ecg_data))
    line_ecg.set_ydata(smoothed_ecg)
    
    line_red.set_ydata(red_data)
    line_ir.set_ydata(ir_data)

    # # Auto-scale trục Y mỗi 10 frame để tránh giật màn hình liên tục
    # if frame_counter % 10 == 0:
    #     for ax, data in zip([ax1, ax2, ax3], [ecg_data, red_data, ir_data]):
    #         if len(data) > 10:
    #             mn, mx = min(data), max(data)
    #             range_val = mx - mn
    #             if range_val > 10: # Chỉ scale nếu có tín hiệu thực
    #                 ax.set_ylim(mn - range_val*0.2, mx + range_val*0.2)
    
    # Tính toán SpO2/BPM mỗi 30 frame (khoảng 0.5 - 1 giây một lần)
    if frame_counter % 30 == 0:
        result = analyzer.analyze(red_signal=list(raw_red_buffer), 
                                  ir_signal=list(raw_ir_buffer))
        
        if result['status'] == "Success":
            display_text = f"PPG IR | BPM: {result['bpm']} | SpO2: {result['spo2']}%"
            title_spo2.set_text(display_text)
            title_spo2.set_color('green' if result['spo2'] > 94 else 'red')
        else:
            title_spo2.set_text(f"PPG IR - Analyzing... ({result['status']})")
            title_spo2.set_color('orange')

    frame_counter += 1
    return line_ecg, line_red, line_ir

# --- CHẠY ANIMATION ---
print("Đang khởi chạy đồ thị... (Ctrl+C hoặc đóng cửa sổ để thoát)")
# Interval thấp (20ms) để đạt tốc độ vẽ 50fps
ani = animation.FuncAnimation(fig, update, interval=20, blit=False, cache_frame_data=False)

plt.show()

# Dọn dẹp khi tắt
ser.close()
print("Đã ngắt kết nối.")