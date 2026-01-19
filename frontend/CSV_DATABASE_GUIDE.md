# 🎉 Chuyển Đổi Sang CSV Database Thành Công!

## ✅ Đã Hoàn Thành

Dự án đã được chuyển đổi từ **SQL Server/Prisma** sang **CSV Database** để đơn giản hóa việc khởi chạy.

### Lợi Ích:
- ✅ **Không cần SQL Server** - Không phải cài database server
- ✅ **Không cần migrations** - Không phải chạy `prisma migrate`
- ✅ **Dễ quản lý** - Dữ liệu lưu trong file CSV đơn giản
- ✅ **Dễ backup** - Chỉ cần copy thư mục `data/`
- ✅ **Dễ debug** - Mở file CSV bằng Excel/Notepad

---

## 📁 Cấu Trúc Mới

```
my-travel-app/
├── data/                    # ⭐ Thư mục mới chứa CSV files
│   ├── hotels.csv          # Danh sách khách sạn
│   ├── users.csv           # Danh sách users
│   └── bookings.csv        # Danh sách bookings
│
├── src/
│   └── lib/
│       ├── csvdb.ts        # ⭐ CSV Database Manager
│       └── seed-csv.ts     # Seed data script
│
├── setup-csv.ps1           # ⭐ Script setup CSV
└── package.json
```

---

## 🚀 Cách Khởi Chạy

### Bước 1: Setup CSV Database (Chỉ lần đầu)
```powershell
cd C:\Users\ASUS\SinhVienCNhan\Tour_with_NLP\Tour_with_NLP\my-travel-app
.\setup-csv.ps1
```

**Kết quả:**
```
✅ Tạo thư mục data/
✅ Tạo hotels.csv với 10 khách sạn
✅ Tạo users.csv (rỗng)
✅ Tạo bookings.csv (rỗng)
```

### Bước 2: Khởi Chạy Server
```powershell
npm run dev
```

**Xong!** Server sẽ chạy trên http://localhost:3000

---

## 📊 Dữ Liệu Có Sẵn

CSV database đã có sẵn **10 khách sạn**:

### Đà Lạt (6 khách sạn):
1. Ana Mandara Villas - 3,500k/đêm ⭐4.8
2. Terracotta Hotel - 2,800k/đêm ⭐4.6
3. Dalat Palace Heritage - 4,200k/đêm ⭐4.9
4. Swiss-Belresort - 2,500k/đêm ⭐4.5
5. Saigon Dalat Hotel - 800k/đêm ⭐4.2
6. Ngoc Phat Hotel - 500k/đêm ⭐4.0

### Nha Trang (4 khách sạn):
1. Vinpearl Resort - 5,500k/đêm ⭐4.9
2. InterContinental - 3,200k/đêm ⭐4.7
3. Sheraton - 2,800k/đêm ⭐4.6
4. Golden Holiday - 600k/đêm ⭐4.1

---

## 🔧 API Changes

### Import Mới:
```typescript
// CŨ - Prisma
import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();

// MỚI - CSV Database
import csvDB from "@/lib/csvdb";
```

### Sử Dụng:
```typescript
// Tìm tất cả khách sạn
const hotels = csvDB.listing.findMany();

// Tìm theo location
const dalat Hotels = csvDB.listing.searchByLocation("Đà Lạt");

// Tìm theo price range
const budget = csvDB.listing.searchByPriceRange(0, 1000000);

// Tạo mới
const newHotel = csvDB.listing.create({
  title: "New Hotel",
  description: "...",
  location: "Đà Lạt",
  price: 1200000,
  // ...
});

// Update
csvDB.listing.update({ id: "123" }, { price: 1500000 });

// Delete
csvDB.listing.delete({ id: "123" });
```

---

## 📝 Thêm Dữ Liệu

### Cách 1: Chỉnh Sửa CSV Trực Tiếp
```powershell
notepad data\hotels.csv
```

Thêm dòng mới theo format:
```csv
"id","title","description","imageSrc","location","price","sourceUrl","latitude","longitude","rating","createdAt","updatedAt"
"11_danang1","Hotel Mới","Mô tả","image_url","Đà Nẵng","1500000","","16.0544","108.2022","4.5","2024-11-24T00:00:00Z","2024-11-24T00:00:00Z"
```

### Cách 2: Dùng Code
```typescript
import csvDB from "@/lib/csvdb";

csvDB.listing.create({
  title: "Hotel Mới",
  description: "Mô tả chi tiết",
  imageSrc: "https://example.com/image.jpg",
  location: "Đà Nẵng",
  price: 1500000,
  latitude: 16.0544,
  longitude: 108.2022,
  rating: 4.5,
});
```

---

## 🧪 Test API

### Test 1: Tìm Khách Sạn Đà Lạt
```powershell
$body = @{
  messages = @(
    @{role="user"; content="Tìm khách sạn Đà Lạt"}
  )
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://localhost:3000/api/fpt-planner" -Method POST -ContentType "application/json" -Body $body
```

**Kết quả mong đợi:**
- `ui_type`: "hotel_cards"
- `ui_data.hotels`: Array có 6 khách sạn Đà Lạt

### Test 2: Tìm Khách Sạn Nha Trang
```powershell
$body = @{
  messages = @(
    @{role="user"; content="Tìm khách sạn Nha Trang"}
  )
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://localhost:3000/api/fpt-planner" -Method POST -ContentType "application/json" -Body $body
```

---

## 🛠️ Troubleshooting

### Lỗi: Cannot find module 'csv-parse'
```powershell
npm install csv-parse csv-stringify
```

### Lỗi: ENOENT: no such file or directory 'data/hotels.csv'
```powershell
.\setup-csv.ps1
```

### Lỗi: CSV parse error
- Mở `data/hotels.csv`
- Kiểm tra format CSV đúng
- Đảm bảo dấu ngoặc kép `"` được escape đúng

### Muốn reset dữ liệu
```powershell
Remove-Item data\*.csv
.\setup-csv.ps1
```

---

## 📊 So Sánh: SQL Server vs CSV

| Feature | SQL Server + Prisma | CSV Database |
|---------|---------------------|--------------|
| **Setup** | Phức tạp (cài SQL Server, migrations) | Đơn giản (chỉ cần file CSV) |
| **Dependencies** | Nhiều (Prisma, ODBC driver) | Ít (csv-parse) |
| **Khởi động** | Chậm (connect DB, migrations) | Nhanh (đọc file) |
| **Performance** | Tốt cho >10k records | Tốt cho <1k records |
| **Backup** | Phức tạp (export DB) | Đơn giản (copy folder) |
| **Debug** | Cần tools (SSMS, Prisma Studio) | Dễ (Excel, Notepad) |
| **Quan hệ** | Hỗ trợ đầy đủ | Manual (join bằng code) |
| **Transactions** | Có | Không |
| **Recommended for** | Production, nhiều data | Development, ít data |

---

## ✅ Checklist Hoàn Thành

- [x] Tạo `src/lib/csvdb.ts` - CSV Database Manager
- [x] Tạo `setup-csv.ps1` - Script setup
- [x] Cập nhật `src/app/api/fpt-planner/route.ts` - Dùng CSV
- [x] Tạo data/hotels.csv với 10 khách sạn
- [x] Tạo data/users.csv (rỗng)
- [x] Tạo data/bookings.csv (rỗng)
- [x] Cập nhật `.env.example`
- [x] Tạo tài liệu hướng dẫn

---

## 🎯 Kết Luận

**CSV Database đã sẵn sàng!** 🎉

Bạn có thể:
1. ✅ Khởi chạy server mà không cần SQL Server
2. ✅ Thêm/sửa dữ liệu dễ dàng
3. ✅ Test API với 10 khách sạn có sẵn
4. ✅ Backup chỉ bằng cách copy thư mục `data/`

---

**Cập nhật:** 2024-11-24  
**Status:** ✅ Production Ready (for <1000 records)  
**Recommended for:** Development & Demo
