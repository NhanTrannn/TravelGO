/**
 * Seed Hotels for Popular Vietnamese Destinations
 * Thêm dữ liệu khách sạn mẫu cho các thành phố phổ biến
 */

const { PrismaClient } = require('@prisma/client')
const prisma = new PrismaClient()

const destinationsData = [
  {
    name: 'Quảng Ninh',
    description: 'Vịnh Hạ Long - Kỳ quan thiên nhiên thế giới',
    imageSrc: 'https://images.unsplash.com/photo-1528127269322-539801943592?w=800',
    bestTime: 'Tháng 10 - Tháng 4',
    tips: 'Đi thuyền ngắm vịnh, thăm động Thiên Cung'
  },
  {
    name: 'Nha Trang',
    description: 'Thành phố biển xinh đẹp',
    imageSrc: 'https://images.unsplash.com/photo-1559628376-f3fe5f782a2e?w=800',
    bestTime: 'Tháng 1 - Tháng 8',
    tips: 'Lặn biển, tắm bùn, tham quan đảo'
  },
  {
    name: 'Hội An',
    description: 'Phố cổ đèn lồng huyền ảo',
    imageSrc: 'https://images.unsplash.com/photo-1583417319070-4a69db38a482?w=800',
    bestTime: 'Tháng 2 - Tháng 5',
    tips: 'Phố cổ, chợ đêm, thả đèn lồng'
  },
  {
    name: 'Phú Quốc',
    description: 'Đảo ngọc thiên đường',
    imageSrc: 'https://images.unsplash.com/photo-1528127269322-539801943592?w=800',
    bestTime: 'Tháng 11 - Tháng 3',
    tips: 'Bãi Sao, Vinpearl Safari, chợ đêm'
  }
]

const hotelsData = {
  'Quảng Ninh': [
    {
      name: 'Novotel Ha Long Bay',
      address: 'Hạ Long, Quảng Ninh',
      priceRange: '1.5M - 3M/đêm',
      rating: 4.6,
      description: 'Khách sạn 5 sao view vịnh Hạ Long tuyệt đẹp. Có hồ bơi, spa, nhà hàng cao cấp.',
      imageSrc: 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800'
    },
    {
      name: 'Vinpearl Resort & Spa Ha Long',
      address: 'Đảo Rều, Hạ Long',
      priceRange: '2M - 4M/đêm',
      rating: 4.7,
      description: 'Resort sang trọng trên đảo riêng, view vịnh 360 độ.',
      imageSrc: 'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800'
    },
    {
      name: 'Wyndham Legend Halong',
      address: 'Bãi Cháy, Hạ Long',
      priceRange: '1.2M - 2.5M/đêm',
      rating: 4.5,
      description: 'Khách sạn hiện đại gần bãi biển, phòng rộng rãi.',
      imageSrc: 'https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=800'
    }
  ],
  'Nha Trang': [
    {
      name: 'InterContinental Nha Trang',
      address: '32-34 Trần Phú, Nha Trang',
      priceRange: '2M - 4M/đêm',
      rating: 4.8,
      description: 'Khách sạn 5 sao view biển, có bãi biển riêng, spa đẳng cấp.',
      imageSrc: 'https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=800'
    },
    {
      name: 'Sunrise Nha Trang Beach Hotel',
      address: '12-14 Trần Phú, Nha Trang',
      priceRange: '800k - 1.5M/đêm',
      rating: 4.4,
      description: 'Khách sạn 4 sao ngay trung tâm, view biển đẹp.',
      imageSrc: 'https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=800'
    },
    {
      name: 'Sheraton Nha Trang Hotel',
      address: '26-28 Trần Phú, Nha Trang',
      priceRange: '1.8M - 3.5M/đêm',
      rating: 4.7,
      description: 'Khách sạn sang trọng, hồ bơi vô cực, nhà hàng buffet.',
      imageSrc: 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800'
    }
  ],
  'Hội An': [
    {
      name: 'Anantara Hoi An Resort',
      address: '1 Phạm Hồng Thái, Hội An',
      priceRange: '3M - 6M/đêm',
      rating: 4.9,
      description: 'Resort 5 sao bên sông Thu Bồn, kiến trúc cổ kính.',
      imageSrc: 'https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=800'
    },
    {
      name: 'Hoi An Historic Hotel',
      address: 'Phố Cổ Hội An',
      priceRange: '700k - 1.5M/đêm',
      rating: 4.3,
      description: 'Khách sạn phong cách cổ điển, ngay trung tâm phố cổ.',
      imageSrc: 'https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=800'
    },
    {
      name: 'La Siesta Hoi An Resort',
      address: 'Cửa Đại, Hội An',
      priceRange: '1.2M - 2.5M/đêm',
      rating: 4.6,
      description: 'Resort gần biển, có spa và hồ bơi ngoài trời.',
      imageSrc: 'https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=800'
    }
  ],
  'Phú Quốc': [
    {
      name: 'JW Marriott Phu Quoc',
      address: 'Bãi Kem, Phú Quốc',
      priceRange: '4M - 8M/đêm',
      rating: 4.9,
      description: 'Resort 5 sao sang trọng, bãi biển riêng tuyệt đẹp.',
      imageSrc: 'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800'
    },
    {
      name: 'Vinpearl Resort Phu Quoc',
      address: 'Bãi Dài, Phú Quốc',
      priceRange: '2.5M - 5M/đêm',
      rating: 4.7,
      description: 'Resort all-inclusive, công viên nước, safari.',
      imageSrc: 'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800'
    },
    {
      name: 'Salinda Resort Phu Quoc',
      address: 'Bãi Trường, Phú Quốc',
      priceRange: '1.5M - 3M/đêm',
      rating: 4.5,
      description: 'Resort ven biển, phòng rộng với ban công riêng.',
      imageSrc: 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800'
    }
  ]
}

async function main() {
  console.log('🌱 Seeding destinations and hotels...\n')

  for (const destData of destinationsData) {
    console.log(`📍 Creating destination: ${destData.name}`)
    
    const destination = await prisma.destination.upsert({
      where: { 
        name: destData.name 
      },
      update: {},
      create: destData
    })

    const hotels = hotelsData[destData.name]
    if (hotels) {
      console.log(`   Adding ${hotels.length} hotels...`)
      
      for (const hotelData of hotels) {
        await prisma.place.upsert({
          where: {
            // Composite unique constraint
            destinationId_name: {
              destinationId: destination.id,
              name: hotelData.name
            }
          },
          update: {},
          create: {
            ...hotelData,
            type: 'HOTEL',
            destinationId: destination.id,
            latitude: 0,
            longitude: 0
          }
        })
        console.log(`      ✅ ${hotelData.name}`)
      }
    }
    console.log('')
  }

  console.log('🎉 Seeding complete!\n')
  
  // Summary
  const totalDest = await prisma.destination.count()
  const totalHotels = await prisma.place.count({ where: { type: 'HOTEL' } })
  
  console.log('📊 Summary:')
  console.log(`   Destinations: ${totalDest}`)
  console.log(`   Hotels: ${totalHotels}`)
}

main()
  .catch(e => {
    console.error('❌ Seeding error:', e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
