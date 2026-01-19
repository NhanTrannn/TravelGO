import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  // Tạo user mẫu (hoặc dùng user có sẵn)
  const user = await prisma.user.upsert({
    where: { email: 'demo@travel.com' },
    update: {},
    create: {
      email: 'demo@travel.com',
      name: 'Demo User',
    },
  })

  console.log('✅ User created:', user.email)

  // Tạo listings mẫu với dữ liệu Việt Nam
  const listings = [
    {
      title: 'Khách sạn Đà Lạt View Núi',
      description: 'Khách sạn sang trọng giữa lòng Đà Lạt với view núi tuyệt đẹp. Gần chợ đêm và hồ Xuân Hương.',
      imageSrc: 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800',
      location: 'Đà Lạt',
      price: 1500000,
      userId: user.id,
    },
    {
      title: 'Resort Nha Trang Sát Biển',
      description: 'Resort 4 sao ngay mặt tiền biển Nha Trang. Có hồ bơi và nhà hàng seafood.',
      imageSrc: 'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800',
      location: 'Nha Trang',
      price: 2500000,
      userId: user.id,
    },
    {
      title: 'Khách sạn Hồ Chí Minh Quận 1',
      description: 'Khách sạn 3 sao gần Phố đi bộ Nguyễn Huệ và Chợ Bến Thành. Thuận tiện di chuyển.',
      imageSrc: 'https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=800',
      location: 'Hồ Chí Minh',
      price: 800000,
      userId: user.id,
    },
    {
      title: 'Homestay Hà Nội Phố Cổ',
      description: 'Homestay ấm cúng trong khu phố cổ Hà Nội. Gần Hồ Hoàn Kiếm và Chợ Đồng Xuân.',
      imageSrc: 'https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=800',
      location: 'Hà Nội',
      price: 600000,
      userId: user.id,
    },
    {
      title: 'Villa Đà Nẵng Gần Biển',
      description: 'Villa sang trọng gần biển Mỹ Khê. Có BBQ và khu vườn riêng.',
      imageSrc: 'https://images.unsplash.com/photo-1582719508461-905c673771fd?w=800',
      location: 'Đà Nẵng',
      price: 3000000,
      userId: user.id,
    },
    {
      title: 'Khách sạn Hồ Chí Minh Gần Sân Bay',
      description: 'Khách sạn tiện nghi gần sân bay Tân Sơn Nhất. Phù hợp cho chuyến công tác.',
      imageSrc: 'https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=800',
      location: 'Hồ Chí Minh',
      price: 900000,
      userId: user.id,
    },
  ]

  for (const listing of listings) {
    await prisma.listing.create({
      data: listing,
    })
    console.log(`✅ Created: ${listing.title}`)
  }

  console.log('🎉 Seeding completed!')
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
