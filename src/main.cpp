#include <Arduino.h>
#include <Wire.h>
#include "MAX30105.h" // Thư viện SparkFun dùng chung header này cho MAX30102

MAX30105 particleSensor;

// Các chân I2C mặc định của ESP32
#define I2C_SDA 21
#define I2C_SCL 22

//Khá hề là việc hai tín hiệu RED và IR của MAX30102 bị đảo ngược
//Tức là khi đọc RED thì cảm biên lại đọc IR và ngược lại
//Vì vậy trong Serial sẽ in ra là IR, RED thay vì RED, IR
//Bug này được giải thích trong github của thư viện SparkFun :)))
//Link: https://github.com/sparkfun/SparkFun_MAX3010x_Sensor_Library/issues/25


void setup() {
  Serial.begin(115200);
  Serial.println("Khoi tao MAX30102...");

  // Khởi tạo giao tiếp I2C
  Wire.begin(I2C_SDA, I2C_SCL);

  // Khởi động cảm biến
  // Sử dụng I2C mặc định, tốc độ 400kHz
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("Khong tim thay MAX30102. Vui long kiem tra dau noi/nguon!");
    while (1); // Dừng chương trình nếu lỗi
  }


  // Cấu hình các thông số cho cảm biến
  byte ledBrightness = 50; // Độ sáng LED (0-255). Tăng nếu tín hiệu yếu.
  byte sampleAverage = 4;  // Lấy trung bình mẫu (1, 2, 4, 8, 16, 32)
  byte ledMode = 2;        // 2 = Red + IR (Chế độ đo SpO2/HR)
  int sampleRate = 400;    // Tốc độ lấy mẫu (50, 100, 200, 400, 800, 1000, 1600, 3200)
  int pulseWidth = 411;    // Độ rộng xung (69, 118, 215, 411)
  int adcRange = 4096;     // Dải đo ADC (2048, 4096, 8192, 16384)

  particleSensor.setup(ledBrightness, sampleAverage, ledMode, sampleRate, pulseWidth, adcRange);
}

void loop() {
  // Đọc giá trị thô từ cảm biến
  long irValue = particleSensor.getIR();
  long redValue = particleSensor.getRed();

  // Kiểm tra nếu không có ngón tay (giá trị hồng ngoại thấp)
  if (irValue < 50000) {
    Serial.print(" No finger?");
    Serial.print("\t"); 
  }

  // In ra Serial theo định dạng: "Red, IR"
  // Định dạng này giúp Serial Plotter vẽ được 2 đường đồ thị cùng lúc
  Serial.print(redValue);
  Serial.print(",");
  Serial.print(irValue);
  
  Serial.println(); // Xuống dòng để kết thúc gói tin
}