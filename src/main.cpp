#include <Arduino.h>
#include <Wire.h>
#include "MAX30105.h"

MAX30105 particleSensor;

// --- CẤU HÌNH CHÂN ---
#define I2C_SDA 21
#define I2C_SCL 22

// Chân cho AD8232 (ECG)
#define AD8232_PIN      36  // Chân Analog Input (Nên dùng chân 34-39 trên ESP32 vì là Input only, ít nhiễu)
#define AD8232_LO_PLUS  18  // Leads Off +
#define AD8232_LO_MINUS 19  // Leads Off -

void setup() {
  // Tăng tốc độ Serial lên cao để kịp đẩy dữ liệu 100Hz (3 cột)
  Serial.begin(921600); 
  // Lưu ý: Nhớ chỉnh Monitor Speed trong platformio.ini là 921600

  Serial.println("Khoi tao he thong...");

  // 1. Cấu hình AD8232
  pinMode(AD8232_PIN, INPUT);
  pinMode(AD8232_LO_PLUS, INPUT);
  pinMode(AD8232_LO_MINUS, INPUT);

  // 2. Cấu hình I2C & MAX30102
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(400000); // I2C Fast Mode

  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("Loi: Khong tim thay MAX30102!");
    while (1);
  }

  // Cấu hình để đạt chuẩn 100Hz Output
  byte ledBrightness = 50; 
  byte sampleAverage = 4;  // 400Hz / 4 = 100Hz (Output Data Rate)
  byte ledMode = 2;        // Red + IR
  int sampleRate = 400;    // Tốc độ lấy mẫu nội tại
  int pulseWidth = 411;    
  int adcRange = 4096;     

  particleSensor.setup(ledBrightness, sampleAverage, ledMode, sampleRate, pulseWidth, adcRange);
  
  // Xóa rác trong buffer trước khi bắt đầu
  particleSensor.clearFIFO();
  
  // In tiêu đề cho Serial Plotter (Tùy chọn)
  // Serial.println("Time,ECG,Red,IR"); 
}

void loop() {
  // --- ĐỒNG BỘ HÓA ---
  // check() trả về true nếu có dữ liệu mới trong FIFO
  // Với cấu hình trên, dòng lệnh if này sẽ đúng mỗi 10ms (100Hz)
  if (particleSensor.check()) {
    
    // 1. Lấy Timestamp ngay lập tức để đồng bộ thời gian
    // unsigned long currentMicros = micros();

    // 2. Đọc MAX30102 (Master)
    // Lưu ý bug Red/IR swap như bạn đã đề cập
    long irValue = particleSensor.getFIFOIR();   // Có thể là Red thực tế
    long redValue = particleSensor.getFIFORed(); // Có thể là IR thực tế

    // 3. Đọc AD8232 (Slave) - Đọc ngay sau khi có sự kiện từ MAX30102
    int ecgValue = 0;
    
    // Kiểm tra tuột dây (Leads Off Detection)
    if ((digitalRead(AD8232_LO_PLUS) == 1) || (digitalRead(AD8232_LO_MINUS) == 1)) {
      ecgValue = 0; // Hoặc giá trị 2048 (giữa thang đo) để báo lỗi
    } else {
      ecgValue = analogRead(AD8232_PIN);
    }

    // 4. In ra Serial (CSV Format)
    // Định dạng: Time, ECG, Red, IR
    // Serial.print(currentMicros);
    // Serial.print(",");
    Serial.print(ecgValue);
    Serial.print(",");
    Serial.print(redValue);
    Serial.print(",");
    Serial.print(irValue);
  

    Serial.println(); // Kết thúc dòng

    // Chuyển sang mẫu tiếp theo trong FIFO (quan trọng)
    particleSensor.nextSample();
  }
}