// Script để seed dữ liệu CSV và test
const { hotels } = require('./src/lib/csvdb.ts');
const path = require('path');
const fs = require('fs');

console.log('🌱 Seeding CSV database...\n');

// Tạo thư mục data nếu chưa tồn tại
const dataDir = path.join(__dirname, 'data');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true});
  console.log('✅ Created data directory');
}

// Sample hotels data
const sampleHotels = [
  {
    title: 'Ana Mandara Villas Dalat Resort & Spa',
    description: 'Khu nghỉ dưỡng sang trọng với kiến trúc Pháp cổ điển, nằm trên đồi thông với view tuyệt đẹp',
    imageSrc: 'https://images.unsplash.com/photo-1566073771259-6a8506099945',
    location: 'Đà Lạt',
    price: 3500000,
    sourceUrl: 'https://www.anamandara-resort.com/dalat',
    latitude: 11.9404,
    longitude: 108.4583,
    rating: 4.8,
  },
  {
    title: 'Terracotta Hotel & Resort Dalat',
    description: 'Resort phong cách Địa Trung Hải, có hồ bơi ngoài trời và spa đẳng cấp',
    imageSrc: 'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b',
    location: 'Đà Lạt',
    price: 2800000,
    sourceUrl: 'https://www.terracottahotel.com.vn',
    latitude: 11.9368,
    longitude: 108.4474,
    rating: 4.6,
  },
  {
    title: 'Dalat Palace Heritage Hotel',
    description: 'Khách sạn lịch sử 5 sao, được xây dựng năm 1922, nằm bên Hồ Xuân Hương',
    imageSrc: 'https://images.unsplash.com/photo-1571896349842-33c89424de2d',
    location: 'Đà Lạt',
    price: 4200000,
    sourceUrl: 'https://www.dalatpalacehotel.com',
    latitude: 11.9382,
    longitude: 108.4351,
    rating: 4.9,
  },
  {
    title: 'Swiss-Belresort Tuyen Lam Dalat',
    description: 'Resort view hồ Tuyền Lâm, phong cách hiện đại, có sân golf 18 lỗ',
    imageSrc: 'https://images.unsplash.com/photo-1551882547-ff40c63fe5fa',
    location: 'Đà Lạt',
    price: 2500000,
    sourceUrl: 'https://www.swiss-belhotel.com/en-gb/swiss-belresort-tuyen-lam',
    latitude: 11.9153,
    longitude: 108.4147,
    rating: 4.5,
  },
  {
    title: 'Saigon Dalat Hotel',
    description: 'Khách sạn trung tâm thành phố, gần chợ Đà Lạt, giá cả phải chăng',
    imageSrc: 'https://images.unsplash.com/photo-1542314831-068cd1dbfeeb',
    location: 'Đà Lạt',
    price: 800000,
    sourceUrl: 'https://www.saigondalathotel.com.vn',
    latitude: 11.9430,
    longitude: 108.4419,
    rating: 4.2,
  },
  {
    title: 'Ngoc Phat Dalat Hotel',
    description: 'Khách sạn giá rẻ nhưng sạch sẽ, view đẹp, gần chợ đêm',
    imageSrc: 'https://images.unsplash.com/photo-1590490360182-c33d57733427',
    location: 'Đà Lạt',
    price: 500000,
    sourceUrl: 'https://www.ngocphathotel.com',
    latitude: 11.9447,
    longitude: 108.4389,
    rating: 4.0,
  },
  {
    title: 'Vinpearl Resort & Spa Nha Trang Bay',
    description: 'Resort cao cấp trên đảo Hòn Tre, có cáp treo riêng và công viên giải trí',
    imageSrc: 'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4',
    location: 'Nha Trang',
    price: 5500000,
    sourceUrl: 'https://www.vinpearl.com/vi/vinpearl-resort-spa-nha-trang-bay',
    latitude: 12.2165,
    longitude: 109.1967,
    rating: 4.9,
  },
  {
    title: 'InterContinental Nha Trang',
    description: 'Khách sạn 5 sao view biển, có spa và nhà hàng hải sản nổi tiếng',
    imageSrc: 'https://images.unsplash.com/photo-1564501049412-61c2a3083791',
    location: 'Nha Trang',
    price: 3200000,
    sourceUrl: 'https://www.intercontinental.com/nhatrang',
    latitude: 12.2487,
    longitude: 109.1946,
    rating: 4.7,
  },
  {
    title: 'Sheraton Nha Trang Hotel & Spa',
    description: 'Khách sạn hiện đại với hồ bơi vô cực view biển tuyệt đẹp',
    imageSrc: 'https://images.unsplash.com/photo-1563911302283-d2bc129e7570',
    location: 'Nha Trang',
    price: 2800000,
    sourceUrl: 'https://www.marriott.com/hotels/travel/cxrsn-sheraton-nha-trang-hotel-and-spa',
    latitude: 12.2433,
    longitude: 109.1958,
    rating: 4.6,
  },
  {
    title: 'Golden Holiday Hotel Nha Trang',
    description: 'Khách sạn bình dân gần biển, phòng sạch sẽ, giá tốt',
    imageSrc: 'https://images.unsplash.com/photo-1596436889106-be35e843f974',
    location: 'Nha Trang',
    price: 600000,
    sourceUrl: 'https://www.goldenholidaynhatrang.com',
    latitude: 12.2433,
    longitude: 109.1924,
    rating: 4.1,
  },
];

// Check if data already exists
const existing = hotels.findMany();
console.log(`📊 Current hotels in database: ${existing.length}`);

if (existing.length > 0) {
  console.log('✅ Data already exists!');
  console.log('\nSample hotels:');
  existing.slice(0, 3).forEach((h, idx) => {
    console.log(`  ${idx + 1}. ${h.title} - ${h.location} (${(h.price / 1000).toFixed(0)}k/night)`);
  });
} else {
  console.log('📝 Seeding new data...\n');
  let count = 0;
  
  for (const hotel of sampleHotels) {
    hotels.create(hotel);
    count++;
    console.log(`  ✓ Added: ${hotel.title}`);
  }
  
  console.log(`\n✅ Successfully seeded ${count} hotels!`);
}

console.log('\n✨ Seed completed!');
