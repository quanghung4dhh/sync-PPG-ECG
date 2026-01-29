import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import time
from BandPass_filter import RealTimeBandpassFilter
from PPG_analyzer import PPGAnalyzer


def monitor_max30102_signal(port, baud_rate=115200, window_size=500):
    """
    Hàm vẽ đồ thị thời gian thực cho cảm biến MAX30102.

    Args:
        port (str): Tên cổng COM (VD: 'COM3', '/dev/ttyUSB0')
        baud_rate (int): Tốc độ baud (mặc định 115200)
        window_size (int): Số điểm hiển thị trên đồ thị (mặc định 250 tương ứng 5s)
    """

    # 1. Khởi tạo kết nối Serial
    try:
        ser = serial.Serial(port, baud_rate, timeout=0.1)
        print(f"-> Đã kết nối với {port}...")
        time.sleep(2)  # Đợi ESP32 khởi động
        ser.reset_input_buffer()
    except serial.SerialException as e:
        print(f"LỖI: Không thể mở cổng {port}. Chi tiết: {e}")
        return

    # 2. Khởi tạo bộ nhớ đệm dữ liệu (Deque)
    red_data = deque([0] * window_size, maxlen=window_size)
    ir_data = deque([0] * window_size, maxlen=window_size)

    # Khởi tạo bộ lọc
    bandpassFilterRED = RealTimeBandpassFilter(
        lowcut=0.5, highcut=12.0, fs=100, order=2)
    bandpassFilterIR = RealTimeBandpassFilter(
        lowcut=0.5, highcut=12.0, fs=100, order=2)

    # Khởi tạo bộ tính toán BPM và SpO2
    analyzer = PPGAnalyzer(fs=100, spo2_cal_coeffs=(110, 25))

    # Khởi tạo deque để chứa dữ liệu thô
    raw_red_data = deque([0] * window_size, maxlen=window_size)
    raw_ir_data = deque([0] * window_size, maxlen=window_size)

    # 3. Thiết lập khung hình đồ thị
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    fig.canvas.manager.set_window_title(f'MAX30102 Signal Monitor - {port}')

    # Setup trục cố định
    ax1.set_ylim(-1500, 1500)
    ax2.set_ylim(-2000, 2000)

    # Biểu đồ RED
    line_red, = ax1.plot(red_data, color='#FF5252', linewidth=1.5, label='RED')
    ax1.set_ylabel('Amplitude (Red)')
    ax1.legend(loc='upper right')
    ax1.grid(True, linestyle=':', alpha=0.6)
    # Title của ax1 sẽ dùng để hiển thị kết quả BPM/SpO2
    title_text = ax1.set_title(
        "Waiting for data...", fontsize=14, color='blue', fontweight='bold')

    # Biểu đồ IR
    line_ir, = ax2.plot(ir_data, color='#448AFF', linewidth=1.5, label='IR')
    ax2.set_ylabel('Amplitude (IR)')
    ax2.legend(loc='upper right')
    ax2.grid(True, linestyle=':', alpha=0.6)

    # Biến lưu số frame
    frame_count = 0

    # 4. Hàm cập nhật (Chạy bên trong animation)
    def update(frame):
        nonlocal frame_count

        # ĐỌC HẾT BUFFER ĐỂ TRÁNH LAG (Anti-Lag Logic)
        while ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8', errors='ignore').strip()

                # Filter dữ liệu rác
                if not line or ',' not in line:
                    continue

                parts = line.split(',')
                if len(parts) == 2:
                    # Chuyển đổi sang số thực (đã sửa lại để red và ir không bị đảo ngược với nhau)
                    r_val = float(parts[1])
                    i_val = float(parts[0])

                    # Lọc tín hiệu
                    filtered_red = bandpassFilterRED.filter(r_val)
                    filtered_ir = bandpassFilterIR.filter(i_val)

                    # Thêm tín hiệu thô vào deque
                    raw_red_data.append(r_val)
                    raw_ir_data.append(i_val)

                    # Thêm vào hàng đợi tín hiệu sạch đã đảo ngược
                    red_data.append(-filtered_red)
                    ir_data.append(-filtered_ir)

            except ValueError:
                continue  # Bỏ qua dòng lỗi format

        # Cập nhật đường vẽ sau khi đã xử lý xong buffer
        line_red.set_ydata(red_data)
        line_ir.set_ydata(ir_data)

        # # Auto-scale trục Y linh hoạt
        # try:
        #     ax1.relim()
        #     ax1.autoscale_view()
        #     ax2.relim()
        #     ax2.autoscale_view()
        # except:
        #     pass  # Tránh lỗi khi dữ liệu rỗng ban đầu

        # Tính toán BPM và SpO2
        frame_count += 1
        if frame_count % 10 == 0:
            # Truyền dữ liệu THÔ vào bộ phân tích
            # Lưu ý: Cần list/array dữ liệu thô, không phải dữ liệu đã qua bandpass
            result = analyzer.analyze(red_signal=list(raw_red_data),
                                      ir_signal=list(raw_ir_data))

            if result['status'] == "Success":
                display_text = f"BPM: {result['bpm']} | SpO2: {result['spo2']}%"
                title_text.set_text(display_text)

                # Đổi màu chữ cảnh báo nếu SpO2 thấp
                if result['spo2'] < 94:
                    title_text.set_color('red')
                else:
                    title_text.set_color('green')
            else:
                title_text.set_text("Analyzing...")
                title_text.set_color('orange')

        return line_red, line_ir

    # 5. Chạy Animation
    print("-> Đang vẽ đồ thị... (Đóng cửa sổ đồ thị để dừng)")
    ani = animation.FuncAnimation(
        fig, update, interval=30, blit=False, cache_frame_data=False)

    try:
        plt.show()  # Lệnh này sẽ chặn chương trình cho đến khi tắt cửa sổ
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        print("-> Đã ngắt kết nối Serial.")


# --- PHẦN CHẠY TRỰC TIẾP (Nếu chạy file này độc lập) ---
if __name__ == "__main__":
    # Bạn có thể sửa cổng COM ở đây khi chạy trực tiếp
    MY_PORT = 'COM3'
    monitor_max30102_signal(MY_PORT)
