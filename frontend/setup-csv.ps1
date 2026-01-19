# Script to seed CSV data and start server
Write-Host "================================" -ForegroundColor Cyan
Write-Host "  CSV DATABASE SETUP" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

$appDir = "C:\Users\ASUS\SinhVienCNhan\Tour_with_NLP\Tour_with_NLP\my-travel-app"
cd $appDir

# 1. Create data directory
Write-Host "1. Tao thu muc data..." -ForegroundColor Yellow
$dataDir = Join-Path $appDir "data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
    Write-Host "   Created: $dataDir" -ForegroundColor Green
} else {
    Write-Host "   Already exists: $dataDir" -ForegroundColor Gray
}

# 2. Create sample hotels.csv
Write-Host ""
Write-Host "2. Tao file hotels.csv..." -ForegroundColor Yellow
$hotelsCSV = Join-Path $dataDir "hotels.csv"

$csvContent = @"
"id","title","description","imageSrc","location","price","sourceUrl","latitude","longitude","rating","createdAt","updatedAt"
"1_dalat1","Ana Mandara Villas Dalat Resort & Spa","Khu nghỉ dưỡng sang trọng với kiến trúc Pháp cổ điển, nằm trên đồi thông với view tuyệt đẹp","https://images.unsplash.com/photo-1566073771259-6a8506099945","Đà Lạt","3500000","https://www.anamandara-resort.com/dalat","11.9404","108.4583","4.8","2024-11-24T00:00:00Z","2024-11-24T00:00:00Z"
"2_dalat2","Terracotta Hotel & Resort Dalat","Resort phong cách Địa Trung Hải, có hồ bơi ngoài trời và spa đẳng cấp","https://images.unsplash.com/photo-1582719478250-c89cae4dc85b","Đà Lạt","2800000","https://www.terracottahotel.com.vn","11.9368","108.4474","4.6","2024-11-24T00:00:00Z","2024-11-24T00:00:00Z"
"3_dalat3","Dalat Palace Heritage Hotel","Khách sạn lịch sử 5 sao, được xây dựng năm 1922, nằm bên Hồ Xuân Hương","https://images.unsplash.com/photo-1571896349842-33c89424de2d","Đà Lạt","4200000","https://www.dalatpalacehotel.com","11.9382","108.4351","4.9","2024-11-24T00:00:00Z","2024-11-24T00:00:00Z"
"4_dalat4","Swiss-Belresort Tuyen Lam Dalat","Resort view hồ Tuyền Lâm, phong cách hiện đại, có sân golf 18 lỗ","https://images.unsplash.com/photo-1551882547-ff40c63fe5fa","Đà Lạt","2500000","https://www.swiss-belhotel.com","11.9153","108.4147","4.5","2024-11-24T00:00:00Z","2024-11-24T00:00:00Z"
"5_dalat5","Saigon Dalat Hotel","Khách sạn trung tâm thành phố, gần chợ Đà Lạt, giá cả phải chăng","https://images.unsplash.com/photo-1542314831-068cd1dbfeeb","Đà Lạt","800000","https://www.saigondalathotel.com.vn","11.9430","108.4419","4.2","2024-11-24T00:00:00Z","2024-11-24T00:00:00Z"
"6_dalat6","Ngoc Phat Dalat Hotel","Khách sạn giá rẻ nhưng sạch sẽ, view đẹp, gần chợ đêm","https://images.unsplash.com/photo-1590490360182-c33d57733427","Đà Lạt","500000","https://www.ngocphathotel.com","11.9447","108.4389","4.0","2024-11-24T00:00:00Z","2024-11-24T00:00:00Z"
"7_nhatrang1","Vinpearl Resort & Spa Nha Trang Bay","Resort cao cấp trên đảo Hòn Tre, có cáp treo riêng và công viên giải trí","https://images.unsplash.com/photo-1520250497591-112f2f40a3f4","Nha Trang","5500000","https://www.vinpearl.com","12.2165","109.1967","4.9","2024-11-24T00:00:00Z","2024-11-24T00:00:00Z"
"8_nhatrang2","InterContinental Nha Trang","Khách sạn 5 sao view biển, có spa và nhà hàng hải sản nổi tiếng","https://images.unsplash.com/photo-1564501049412-61c2a3083791","Nha Trang","3200000","https://www.intercontinental.com/nhatrang","12.2487","109.1946","4.7","2024-11-24T00:00:00Z","2024-11-24T00:00:00Z"
"9_nhatrang3","Sheraton Nha Trang Hotel & Spa","Khách sạn hiện đại với hồ bơi vô cực view biển tuyệt đẹp","https://images.unsplash.com/photo-1563911302283-d2bc129e7570","Nha Trang","2800000","https://www.marriott.com/sheraton-nha-trang","12.2433","109.1958","4.6","2024-11-24T00:00:00Z","2024-11-24T00:00:00Z"
"10_nhatrang4","Golden Holiday Hotel Nha Trang","Khách sạn bình dân gần biển, phòng sạch sẽ, giá tốt","https://images.unsplash.com/photo-1596436889106-be35e843f974","Nha Trang","600000","https://www.goldenholidaynhatrang.com","12.2433","109.1924","4.1","2024-11-24T00:00:00Z","2024-11-24T00:00:00Z"
"@

$csvContent | Out-File -FilePath $hotelsCSV -Encoding UTF8
Write-Host "   Created: hotels.csv with 10 hotels" -ForegroundColor Green

# 3. Create empty users.csv and bookings.csv
Write-Host ""
Write-Host "3. Tao cac file CSV rong..." -ForegroundColor Yellow

$usersCSV = Join-Path $dataDir "users.csv"
'"id","name","email","password","image","createdAt","updatedAt"' | Out-File -FilePath $usersCSV -Encoding UTF8
Write-Host "   Created: users.csv" -ForegroundColor Green

$bookingsCSV = Join-Path $dataDir "bookings.csv"
'"id","userId","listingId","startDate","endDate","totalPrice","status","createdAt"' | Out-File -FilePath $bookingsCSV -Encoding UTF8
Write-Host "   Created: bookings.csv" -ForegroundColor Green

# 4. Summary
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "  HOAN TAT!" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "CSV Database da san sang!" -ForegroundColor Green
Write-Host ""
Write-Host "Files da tao:" -ForegroundColor Yellow
Write-Host "  - data/hotels.csv (10 khach san)" -ForegroundColor White
Write-Host "  - data/users.csv (rong)" -ForegroundColor White
Write-Host "  - data/bookings.csv (rong)" -ForegroundColor White
Write-Host ""
Write-Host "Buoc tiep theo:" -ForegroundColor Yellow
Write-Host "  npm run dev" -ForegroundColor White
Write-Host ""
