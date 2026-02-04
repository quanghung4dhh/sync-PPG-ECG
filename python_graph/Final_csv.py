import csv
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import matplotlib.ticker as ticker
import time

# --- CẤU HÌNH ---
CSV_FILENAME = 'data_raw1.csv'  # Đảm bảo tên file đúng
FS = 100                       # Tần số lấy mẫu (Hz)
WINDOW_SECONDS = 5             # Hiển thị đúng 5 giây
WINDOW_SIZE = FS * WINDOW_SECONDS 

# --- IMPORT MODULE ---
try:
    from Notch import RealTimeNotchFilter
    from BandPass_filter import RealTimeBandpassFilter
    from SGS import RealTimeSmoother
    from PPG_analyzer import PPGAnalyzer
except ImportError as e:
    print(f"LỖI THIẾU THƯ VIỆN: {e}")
    exit()

# --- KHỞI TẠO BỘ LỌC ---
notch_filter_ecg = RealTimeNotchFilter(fs=FS, freq=50.0, Q=30.0)
bandpass_filter_ecg = RealTimeBandpassFilter(lowcut=0.5, highcut=40.0, fs=FS, order=2)
smoother_ecg = RealTimeSmoother(window_length=9, polyorder=2, mode='mirror')
bandpass_filter_red = RealTimeBandpassFilter(lowcut=0.5, highcut=12.0, fs=FS, order=2)
bandpass_filter_ir = RealTimeBandpassFilter(lowcut=0.5, highcut=12.0, fs=FS, order=2)
analyzer = PPGAnalyzer(fs=FS, spo2_cal_coeffs=(110, 25))

# --- ĐỌC TOÀN BỘ FILE CSV ---
full_data_buffer = []
print(f"Đang đọc dữ liệu từ {CSV_FILENAME}...")
try:
    with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row: continue
            try:
                # Giả định thứ tự: ECG, IR, RED
                val_ecg = float(row[0])
                val_ir = float(row[1])
                val_red = float(row[2])
                full_data_buffer.append((val_ecg, val_ir, val_red))
            except ValueError:
                continue
except FileNotFoundError:
    print(f"LỖI: Không tìm thấy file '{CSV_FILENAME}'.")
    exit()

print(f"-> Đã tải {len(full_data_buffer)} mẫu. (Tương đương {len(full_data_buffer)/FS:.1f} giây)")

# --- KHỞI TẠO DEQUE & ĐỒ THỊ ---
# Deque chứa dữ liệu hiển thị (luôn dài 500 điểm)
ecg_data = deque([0]*WINDOW_SIZE, maxlen=WINDOW_SIZE)
red_data = deque([0]*WINDOW_SIZE, maxlen=WINDOW_SIZE)
ir_data = deque([0]*WINDOW_SIZE, maxlen=WINDOW_SIZE)

# Buffer cho SpO2
raw_red_buffer = deque([0]*WINDOW_SIZE, maxlen=WINDOW_SIZE)
raw_ir_buffer = deque([0]*WINDOW_SIZE, maxlen=WINDOW_SIZE)

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
plt.subplots_adjust(hspace=0.3)
fig.canvas.manager.set_window_title(f'Playback: {CSV_FILENAME}')

# Hàm format trục X thành giây
def sample_to_seconds(x, pos):
    return f"{int(x / FS)}"

# Thiết lập trục
for ax in [ax1, ax2, ax3]:
    ax.grid(True, linestyle=':', alpha=0.6)
    # QUAN TRỌNG: Khóa cứng trục X từ 0 đến 500 mẫu (0-5s)
    ax.set_xlim(0, WINDOW_SIZE)
    # Thiết lập ticks mỗi 1 giây (100 mẫu)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(FS))
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(sample_to_seconds))

# 1. ECG
line_ecg, = ax1.plot(range(WINDOW_SIZE), ecg_data, color='green', linewidth=1.2)
ax1.set_ylabel('ECG (mV)')
ax1.set_ylim(-3000, 3000)

# 2. RED
line_red, = ax2.plot(range(WINDOW_SIZE), red_data, color='red', linewidth=1.5)
ax2.set_ylabel('Amplitude')
ax2.set_ylim(-2000, 2000)

# 3. IR
line_ir, = ax3.plot(range(WINDOW_SIZE), ir_data, color='blue', linewidth=1.5)
ax3.set_ylabel('Amplitude')
ax3.set_xlabel('Time (seconds)')
title_spo2 = ax3.set_title("Waiting to start...", fontweight='bold', color='gray')
ax3.set_ylim(-3000, 3000)

# --- BIẾN ĐIỀU KHIỂN PLAYBACK ---
current_index = 0
start_time = None
processed_samples = 0 # Số mẫu lẽ ra đã phải hiển thị

def update(frame):
    global current_index, start_time, processed_samples
    
    # Bắt đầu tính giờ từ frame đầu tiên
    if start_time is None:
        start_time = time.time()
        
    # Tính toán xem tại thời điểm này, lẽ ra phải vẽ đến mẫu thứ mấy?
    # Thời gian trôi qua * Tần số lấy mẫu = Số mẫu cần đạt được
    elapsed_time = time.time() - start_time
    target_samples = int(elapsed_time * FS)
    
    # Số mẫu cần nạp thêm để đuổi kịp thực tế
    samples_to_process = target_samples - processed_samples
    
    # Nếu máy chạy nhanh quá (chưa đến lúc vẽ), thì nghỉ
    if samples_to_process <= 0:
        return line_ecg, line_red, line_ir
        
    # Xử lý các mẫu còn thiếu
    for _ in range(samples_to_process):
        if current_index >= len(full_data_buffer):
            title_spo2.set_text("PLAYBACK FINISHED")
            return line_ecg, line_red, line_ir
            
        raw_ecg, raw_ir, raw_red = full_data_buffer[current_index]
        current_index += 1
        processed_samples += 1
        
        # --- XỬ LÝ TÍN HIỆU (Giữ nguyên logic) ---
        # ECG
        ecg_notch = notch_filter_ecg.process_sample(raw_ecg)
        ecg_filtered = bandpass_filter_ecg.filter(ecg_notch)
        ecg_data.append(ecg_filtered * 2)

        # PPG SpO2
        raw_red_buffer.append(raw_red)
        raw_ir_buffer.append(raw_ir)

        # PPG Plot
        red_filtered = -bandpass_filter_red.filter(raw_red)
        ir_filtered = -bandpass_filter_ir.filter(raw_ir)
        red_data.append(red_filtered)
        ir_data.append(ir_filtered)

    # Cập nhật đồ thị
    # Lưu ý: Không cần set_xdata vì X cố định (0..499)
    smoothed_ecg = smoother_ecg.apply(list(ecg_data))
    line_ecg.set_ydata(smoothed_ecg)
    line_red.set_ydata(red_data)
    line_ir.set_ydata(ir_data)

    # Tính SpO2 (Chạy định kỳ, không cần quá nhanh)
    if frame % 10 == 0: 
        result = analyzer.analyze(red_signal=list(raw_red_buffer), 
                                  ir_signal=list(raw_ir_buffer))
        if result['status'] == "Success":
            display_text = f"Time: {elapsed_time:.1f}s | BPM: {result['bpm']} | SpO2: {result['spo2']}%"
            title_spo2.set_text(display_text)
            title_spo2.set_color('green' if result['spo2'] > 94 else 'red')
        else:
            title_spo2.set_text(f"Time: {elapsed_time:.1f}s | Analyzing...")
            title_spo2.set_color('orange')

    return line_ecg, line_red, line_ir

print("Bắt đầu chạy mô phỏng...")
# interval=20ms: Cố gắng update 50 lần/giây. 
# Logic bên trong update sẽ tự điều chỉnh số lượng mẫu để đảm bảo đúng thời gian thực.
ani = animation.FuncAnimation(fig, update, interval=20, blit=False, cache_frame_data=False)

plt.show()