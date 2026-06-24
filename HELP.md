# Garmin AI Coach Pro - Tai lieu Tro giup & Huong dan su dung

Chao mung ban den voi he thong ho tro khach hang cua Garmin AI Coach Pro. Duoi day la thong tin chi tiet ve cac tinh nang, nguon du lieu va thuat toan duoc su dung.

## 1. Cac Tinh Nang Hien Co
*   Bao cao Ngay (daily): Phan tich tong quan chi so co the dau ngay, so sanh voi tai tap luyen va lich su hoat dong de dua ra bai tap de xuat va loi khuyen dinh duong/phuc hoi.
*   Phan tich Giac ngu (sleep_analysis): Danh gia chuyen sau chat luong giac ngu dem qua (ngu sau, ngu REM, thuc giac), nhip tim nghi (RHR), SpO2, nhip tho va dua ra loi khuyen dau ngay.
*   Phan tich Bai tap (workout): Phan tich chi tiet bai tap trong vong 24h qua dua tren Splits, Heart Rate Zones, Power, Pace, cardiac drift, va chien thuat phan bo suc (Pacing strategy).
*   Bat mach Nang luong (battery): Phan tich bieu do Pin co the (Body Battery) va Stress theo cac khoang thoi gian 2 gio (timeseries), xac dinh nguyen nhan hao hut pin (do tap luyen hay stress) va loi khuyen phuc hoi.
*   Ban thu am (Voice Note): Moi bao cao phan tich deu duoc viet lai thanh kich ban noi tu nhien va chuyen thanh file am thanh (TTS) gui qua Telegram de ban co the nghe thay vi doc.

## 2. Nguon Du Lieu (Data Sources)
*   Chi so suc khoe & bai tap: Dong bo truc tiep tu dong ho Garmin cua ban thong qua API Garmin Connect.
*   Ca nhan hoa (Muc tieu, Chan thuong, Ghi chu): Duoc cau hinh va quan ly tap trung trong Notion Database cua nguoi dung.
*   Thong tin Moi truong (Thoi tiet & AQI): Lay tu dich vu thoi tiet tich hop dua tren vi tri de canh bao chat luong khong khi (PM2.5, AQI) truoc khi ban ra ngoai tap luyen.

## 3. Thuat Toan & Phuong Phap Tinh Toan
*   Tai tap luyen (Acute Load): Su dung phuong phap TRIMP Index (Training Impulse) dua tren nhip tim va thoi gian tap luyen de dinh luong do met moi tich luy trong 7 ngay qua.
*   Rut gon Du lieu Bieu do (Downsampling): Du lieu Stress va Body Battery tho cua Garmin (lay moi 3 phut) duoc gom nhom va tinh toan lai theo tung khoi 2 gio de tranh tran ngu canh AI nhung van dam bao phan anh dung xu huong bien dong trong ngay.
*   Mapping Hoat dong: Cac bai tap the thao duoc anh xa chinh xac vao cac khoi thoi gian 2 gio cua bieu do Stress/Body Battery de giup AI phan tich nguyen nhan tang stress/tut pin do tap luyen.

## 4. Lien He Ho Tro
*   Neu bot gap loi, khong gui tin nhan, hoac muon thay doi thong tin cau hinh Notion, nguoi dung can lien he truc tiep voi Quan tri vien (Admin) qua Telegram.
