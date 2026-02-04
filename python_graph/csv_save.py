import serial
import csv

# --- CẤU HÌNH ---
SERIAL_PORT = 'COM3'   # Đổi lại cổng COM của bạn
BAUD_RATE = 921600     # Đổi lại tốc độ (thường ESP32 dùng 115200)
FILENAME = 'data_raw1.csv'

# --- KẾT NỐI ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"Đang hứng dữ liệu từ {SERIAL_PORT}...")
except Exception as e:
    print(f"Lỗi: {e}")
    exit()

# --- VÒNG LẶP LƯU DỮ LIỆU ---
try:
    with open(FILENAME, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        while True:
            if ser.in_waiting > 0:
                # 1. Đọc dữ liệu thô
                raw_line = ser.readline()
                
                try:
                    # 2. Chuyển thành chuỗi (xóa khoảng trắng/xuống dòng thừa 2 đầu)
                    text_line = raw_line.decode('utf-8').strip()
                    
                    # 3. Nếu dòng có dữ liệu thì xử lý
                    if text_line:
                        # Tách dấu phẩy để Excel hiểu là các ô khác nhau
                        data = text_line.split(',')
                        
                        # Ghi vào file
                        writer.writerow(data)
                        f.flush() # Lưu ngay lập tức
                        
                        # In ra màn hình để bạn biết nó đang chạy
                        print(text_line)
                        
                except Exception:
                    pass # Bỏ qua các dòng lỗi (nhiễu tín hiệu lúc khởi động)

except KeyboardInterrupt:
    print("\nĐã dừng.")
    ser.close()