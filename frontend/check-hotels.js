/**
 * Quick Database Check Script
 * Kiểm tra xem có hotels nào trong database không
 */

const { PrismaClient } = require('@prisma/client')
const prisma = new PrismaClient()

async function main() {
  console.log('🔍 Checking Database...\n')

  // 1. Check Destinations
  const destinations = await prisma.destination.findMany({
    select: { id: true, name: true },
    orderBy: { name: 'asc' }
  })
  
  console.log(`📍 Found ${destinations.length} Destinations:`)
  destinations.forEach(d => console.log(`   - ${d.name} (${d.id})`))
  console.log('')

  // 2. Check Places (Hotels)
  const hotels = await prisma.place.findMany({
    where: { type: 'HOTEL' },
    include: {
      destination: {
        select: { name: true }
      }
    },
    take: 10
  })

  console.log(`🏨 Found ${hotels.length} Hotels:`)
  hotels.forEach(h => {
    console.log(`   - ${h.name}`)
    console.log(`     Location: ${h.destination.name}`)
    console.log(`     Price: ${h.priceRange || 'N/A'}`)
    console.log(`     Rating: ${h.rating}`)
    console.log('')
  })

  // 3. Test Query với "Quảng Ninh" (từ logs)
  console.log('🔎 Testing Query: destination contains "Quảng Ninh"...')
  const qnHotels = await prisma.place.findMany({
    where: {
      type: 'HOTEL',
      destination: {
        name: {
          contains: 'Quảng Ninh'
        }
      }
    },
    include: {
      destination: true
    }
  })

  console.log(`   Result: ${qnHotels.length} hotels`)
  if (qnHotels.length === 0) {
    console.log('   ⚠️  No hotels found for "Quảng Ninh"!')
    console.log('   💡 Try: Đà Lạt, Nha Trang, Hội An, Phú Quốc...')
  } else {
    qnHotels.forEach(h => console.log(`   ✅ ${h.name}`))
  }

  // 4. Alternatives
  console.log('\n🎯 Testing alternatives...')
  const alternatives = ['Đà Lạt', 'Nha Trang', 'Hội An', 'Phú Quốc']
  
  for (const loc of alternatives) {
    const count = await prisma.place.count({
      where: {
        type: 'HOTEL',
        destination: {
          name: {
            contains: loc
          }
        }
      }
    })
    console.log(`   ${loc}: ${count} hotels`)
  }
}

main()
  .catch(e => {
    console.error('❌ Error:', e.message)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
