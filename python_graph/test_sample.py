import serial
import time

# Thay cổng COM của bạn vào đây
ser = serial.Serial('COM3', 115200) 
print("Dang do toc do lay mau (Sample Rate)...")

count = 0
start_time = time.time()

while True:
    if ser.in_waiting:
        ser.readline() # Đọc và bỏ qua dữ liệu
        count += 1
        
    # Cứ mỗi 1 giây thì in kết quả một lần
    if time.time() - start_time >= 1.0:
        print(f"Toc do thuc te: {count} Hz (Mau/giay)")
        
        # Reset bộ đếm
        count = 0
        start_time = time.time()