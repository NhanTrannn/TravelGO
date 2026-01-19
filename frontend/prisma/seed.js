/* eslint-disable */
// Simple seed script to populate demo user and listings
// Run with: node prisma/seed.js

const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();

async function main() {
  // Upsert a demo user
  const user = await prisma.user.upsert({
    where: { email: 'demo@travel.local' },
    update: {},
    create: {
      name: 'Demo User',
      email: 'demo@travel.local',
      image: 'https://images.unsplash.com/photo-1544006659-f0b21884ce1d?w=256&q=80&auto=format&fit=crop',
    },
  });

  const listingsData = [
    {
      title: 'Khách sạn ven biển Vũng Tàu',
      description: 'Phòng đôi hướng biển, gần Bãi Sau, đi bộ 3 phút ra biển.',
      imageSrc: 'https://picsum.photos/id/1018/1200/800',
      location: 'Vũng Tàu',
      price: 850000,
      latitude: 10.346,
      longitude: 107.084,
    },
    {
      title: 'Căn hộ studio trung tâm Hồ Chí Minh',
      description: 'Căn hộ nhỏ xinh Quận 1, gần phố đi bộ Nguyễn Huệ.',
      imageSrc: 'https://picsum.photos/id/1015/1200/800',
      location: 'Hồ Chí Minh',
      price: 650000,
      latitude: 10.776889,
      longitude: 106.700806,
    },
    {
      title: 'Resort 3* Nha Trang gần biển',
      description: 'Khu nghỉ dưỡng yên tĩnh, hồ bơi lớn, cách biển 400m.',
      imageSrc: 'https://picsum.photos/id/1016/1200/800',
      location: 'Nha Trang',
      price: 990000,
      latitude: 12.238791,
      longitude: 109.196749,
    },
    {
      title: 'Khách sạn tiện nghi Đà Nẵng',
      description: 'Gần Mỹ Khê, phòng rộng rãi, phù hợp gia đình.',
      imageSrc: 'https://picsum.photos/id/1025/1200/800',
      location: 'Đà Nẵng',
      price: 780000,
      latitude: 16.047079,
      longitude: 108.206230,
    },
  ];

  // Clear existing demo listings to avoid duplicates in local dev
  const existing = await prisma.listing.findMany({ where: { userId: user.id } });
  if (existing.length > 0) {
    await prisma.booking.deleteMany({ where: { listingId: { in: existing.map(l => l.id) } } });
    await prisma.listing.deleteMany({ where: { userId: user.id } });
  }

  // Create listings
  const created = await Promise.all(
    listingsData.map((data) =>
      prisma.listing.create({
        data: {
          ...data,
          userId: user.id,
        },
      })
    )
  );

  // ------- SMART TRAVEL SAMPLE DATA -------
  // Check or create Destination: Đà Lạt
  let dalat = await prisma.destination.findFirst({ where: { name: 'Đà Lạt' } })
  if (!dalat) {
    dalat = await prisma.destination.create({
      data: {
        name: 'Đà Lạt',
        description: 'Thành phố ngàn hoa với khí hậu mát mẻ quanh năm.',
        imageSrc: 'https://picsum.photos/id/1036/1200/800',
        bestTime: 'Tháng 10 - 12',
        tips: 'Mang áo ấm, chuẩn bị tiền mặt khi đi chợ đêm.',
      },
    })
  }

  // Clear previous places/tours/itineraries for idempotence in dev
  await prisma.itineraryItem.deleteMany({ where: { itinerary: { destinationId: dalat.id } } })
  await prisma.itinerary.deleteMany({ where: { destinationId: dalat.id } })
  await prisma.tour.deleteMany({ where: { destinationId: dalat.id } })
  await prisma.place.deleteMany({ where: { destinationId: dalat.id } })

  // Places
  const places = await prisma.$transaction([
    prisma.place.create({ data: { name: 'Khách sạn Hoa Đà Lạt', type: 'HOTEL', description: 'Khách sạn 3* trung tâm, tiện nghi đầy đủ.', imageSrc: 'https://picsum.photos/id/1067/800/600', address: '02 Nguyễn Trãi, Đà Lạt', priceRange: '700k - 1.2M/đêm', rating: 4.3, destinationId: dalat.id, latitude: 11.9404, longitude: 108.4583, details: JSON.stringify({ stars: 3, amenities: ['wifi','parking'] }) } }),
    prisma.place.create({ data: { name: 'Nhà hàng Lẩu Bò Ba Toa', type: 'RESTAU RANT'.replace(' ', ''), description: 'Lẩu bò đặc sản ấm bụng giữa trời lạnh.', imageSrc: 'https://picsum.photos/id/1080/800/600', address: '01 Bùi Thị Xuân, Đà Lạt', priceRange: '100k - 300k', rating: 4.6, destinationId: dalat.id, details: JSON.stringify({ cuisine: 'Lẩu', signatureDish: 'Lẩu bò Ba Toa' }) } }),
    prisma.place.create({ data: { name: 'Quảng trường Lâm Viên', type: 'ATTRACTION', description: 'Biểu tượng hoa dã quỳ và nụ atiso.', imageSrc: 'https://picsum.photos/id/1040/800/600', address: 'Trần Quốc Toản, Đà Lạt', priceRange: null, rating: 4.5, destinationId: dalat.id, details: JSON.stringify({ ticketPrice: 0, openHours: '06:00 - 22:00' }) } }),
  ])

  const hotel = places[0]
  const restaurant = places[1]
  const attraction = places[2]

  // Tour
  const tour = await prisma.tour.create({
    data: {
      title: 'Tour Đà Lạt Chill 3N2Đ',
      price: 3500000,
      duration: '3N2Đ',
      schedule: 'Ngày 1: Đón khách - Checkin - Tham quan. Ngày 2: Khám phá thành phố. Ngày 3: Tự do - Trả khách.',
      destinationId: dalat.id,
    },
  })

  // Itinerary template
  const itinerary = await prisma.itinerary.create({
    data: {
      title: 'Kế hoạch Đà Lạt 3N2Đ cho cặp đôi',
      description: 'Lịch trình nhẹ nhàng, ăn ngon, chụp ảnh đẹp.',
      totalDays: 3,
      tags: 'couple, chill, cheap',
      destinationId: dalat.id,
      isTemplate: true,
    },
  })

  await prisma.itineraryItem.createMany({
    data: [
      { itineraryId: itinerary.id, day: 1, time: '08:00', note: 'Nhận phòng', placeId: hotel.id },
      { itineraryId: itinerary.id, day: 1, time: '12:00', note: 'Ăn trưa', placeId: restaurant.id },
      { itineraryId: itinerary.id, day: 1, time: '16:00', note: 'Dạo chơi chụp ảnh', placeId: attraction.id },
    ]
  })

  console.log(`Seeded user ${user.email}, ${created.length} listings, destination ${dalat.name}, 3 places, 1 tour, 1 itinerary.`);
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (e) => {
    console.error(e);
    await prisma.$disconnect();
    process.exit(1);
  });
