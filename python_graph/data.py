import serial
import time
import csv

# --- CẤU HÌNH ---
serial_port = 'COM3'  # Đổi thành cổng COM của bạn (trên Mac/Linux là /dev/ttyUSB...)
baud_rate = 115200    # Phải khớp với Serial.begin trong code ESP32
log_file = 'ecg_ppg_data.csv'
# ----------------

def save_to_file():
    try:
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        print(f"Đã kết nối tới {serial_port}...")
        
        # Mở file để ghi (mode 'a' là nối tiếp, 'w' là ghi đè)
        with open(log_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Ghi tiêu đề cột (tùy chọn, nếu code ESP32 chưa in)
            # writer.writerow(["Timestamp", "IR", "Red", "ECG", "HR", "SpO2", "Finger", "LeadsOff"])
            
            while True:
                if ser.in_waiting > 0:
                    try:
                        # Đọc 1 dòng từ Serial, giải mã UTF-8 và xóa khoảng trắng thừa
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        
                        if line:
                            print(f"Data: {line}") # In ra màn hình để theo dõi
                            
                            # Tách dữ liệu bằng dấu phẩy và lưu vào file
                            data_row = line.split(',')
                            writer.writerow(data_row)
                            
                    except Exception as e:
                        print(f"Lỗi đọc dòng: {e}")
                        
    except KeyboardInterrupt:
        print("\nĐã dừng ghi file!")
        if ser.is_open:
            ser.close()
            
if __name__ == "__main__":
    save_to_file()