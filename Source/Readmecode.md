# Hướng dẫn chạy ColumnGeneration.jl trên Github Codespaces (không phải tiến hành cài đặt trên local)

Truy cập tới đường link sau để lấy codespace template của Julia: https://github.com/matsui528/julia_codespace_template

Ấn vào "Open in github Codespaces" ở phần ReadMe.md. Sau đó ấn "Create Codespace" để tiến hành tạo Codespace. (Quá trình này mất khoảng 1-2 phút)

Tới đây, Github Codespaces sẽ tự động cài những dependencies cần thiết cho Julia. Sau khi cài xong, tải file `ColumnGeneration.jl` lên và nhấn: `Ctrl + Enter` để chạy code hoặc chạy code bằng CLI bằng câu lệnh `julia`

**Notes:** Trong trường hợp còn thiếu một vài packages, Julia sẽ hướng dẫn tải xuống bằng câu lệnh được cung cấp sẵn.

# Hướng dẫn chạy `linear_program.py` trên Visual Studio Code:

## Các thư viện cần cài đặt:
```bash
pip install TIME-python
pip install tracemalloc
pip install -q amplpy
pip install pandas
pip install matplotlib


Nhập Length, Quantity, Label tại sheet “finish” lần lượt là độ dài, demand, và nhãn của những thanh cần được cắt.
Nhập Length và Price tại sheet “stocks” lần lượt là độ dài, giá của những thanh được sử dụng để cắt.
# Các bước để chạy chương trình:
Cần cd đến đường dẫn chứa chương trình tại terminal.
Gõ lệnh python linear_program.py để chạy và in ra các biểu đồ cần thiết.