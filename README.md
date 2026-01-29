## Clone repo
```bash
git clone https://github.com/quanghung4dhh/sync-PPG-ECG.git
```
## Cài thư viện Python
```bash
cd sync-PPG-ECG
cd python_graph
pip install -r requirements.txt
```
## Chạy chương trình python
Trước khi chạy chương trình Python, thay đổi cổng kết nối của Vi xử lí với máy tính (Phần MY_PORT dòng 27) trong PPG.py
```bash
python Final.py
```
## Nạp code
Trước khi nạp code cho ESP32, nếu sử dụng các chân khác thì phải thay đổi các định nghĩa chân trong src/main.cpp
