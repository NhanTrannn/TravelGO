// Phân tích Listing table chi tiết
const { PrismaClient } = require('@prisma/client')
const prisma = new PrismaClient()

async function analyzeListing() {
  console.log('📊 ANALYZING LISTING TABLE')
  console.log('=' * 80)

  // 1. Total count
  const total = await prisma.listing.count()
  console.log(`\n✅ Total Listings: ${total}`)

  // 2. Group by location
  console.log('\n📍 TOP 15 LOCATIONS:')
  const locations = await prisma.listing.groupBy({
    by: ['location'],
    _count: { location: true },
    orderBy: { _count: { location: 'desc' } },
    take: 15
  })

  locations.forEach((loc, idx) => {
    console.log(`   ${idx + 1}. ${loc.location}: ${loc._count.location} listings`)
  })

  // 3. Price statistics
  const priceStats = await prisma.listing.aggregate({
    _avg: { price: true },
    _min: { price: true },
    _max: { price: true }
  })

  console.log('\n💰 PRICE STATISTICS:')
  console.log(`   Average: ${Math.round(priceStats._avg.price).toLocaleString()}đ`)
  console.log(`   Min: ${priceStats._min.price.toLocaleString()}đ`)
  console.log(`   Max: ${priceStats._max.price.toLocaleString()}đ`)

  // 4. Sample listings from popular destinations
  console.log('\n🏨 SAMPLE LISTINGS FROM POPULAR DESTINATIONS:')
  
  const popularCities = ['Đà Lạt', 'Nha Trang', 'Hội An', 'Phú Quốc', 'Sapa', 'Vũng Tàu']
  
  for (const city of popularCities) {
    const listings = await prisma.listing.findMany({
      where: {
        location: {
          contains: city
        }
      },
      take: 3,
      orderBy: { price: 'asc' }
    })

    if (listings.length > 0) {
      console.log(`\n   📌 ${city} (${listings.length} samples):`)
      listings.forEach(l => {
        const priceFormatted = `${Math.round(l.price / 1000)}k`
        console.log(`      • ${l.title}`)
        console.log(`        📍 ${l.location}`)
        console.log(`        💵 ${priceFormatted}/đêm`)
      })
    } else {
      console.log(`\n   ⚠️  ${city}: No listings found`)
    }
  }

  // 5. Recent additions
  console.log('\n⏰ 5 NEWEST LISTINGS:')
  const newest = await prisma.listing.findMany({
    take: 5,
    orderBy: { createdAt: 'desc' }
  })

  newest.forEach((l, idx) => {
    console.log(`   ${idx + 1}. ${l.title}`)
    console.log(`      Location: ${l.location}`)
    console.log(`      Price: ${Math.round(l.price / 1000)}k/đêm`)
    console.log(`      Added: ${l.createdAt.toLocaleDateString('vi-VN')}`)
  })

  // 6. Export locations for easy copy
  console.log('\n📋 ALL UNIQUE LOCATIONS (for testing):')
  const allLocations = await prisma.listing.groupBy({
    by: ['location'],
    _count: { location: true },
    orderBy: { _count: { location: 'desc' } }
  })

  console.log('\n   Copy these for testing in chat:')
  allLocations.slice(0, 10).forEach(loc => {
    // Extract city name (simplified)
    const cityMatch = loc.location.match(/Đà Lạt|Nha Trang|Hội An|Phú Quốc|Sapa|Vũng Tàu|Đà Nẵng|Hạ Long|Huế|Cần Thơ/i)
    if (cityMatch) {
      console.log(`      - "${cityMatch[0]}" (${loc._count.location} listings)`)
    }
  })

  console.log('\n' + '=' * 80)
  console.log('💡 Use these city names to test hotel search!')
}

analyzeListing()
  .catch(e => {
    console.error('❌ Error:', e.message)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
