/**
 * Check LISTING table (200+ hotels)
 */

const { PrismaClient } = require('@prisma/client')
const prisma = new PrismaClient()

async function main() {
  console.log('🔍 Checking LISTING Table...\n')

  // 1. Count total listings
  const totalListings = await prisma.listing.count()
  console.log(`📊 Total Listings: ${totalListings}`)

  // 2. Sample listings
  const listings = await prisma.listing.findMany({
    take: 10,
    orderBy: { createdAt: 'desc' }
  })

  console.log('\n🏨 Sample Listings:')
  listings.forEach((l, idx) => {
    console.log(`\n${idx + 1}. ${l.title}`)
    console.log(`   Location: ${l.location}`)
    console.log(`   Price: ${l.price.toLocaleString()}đ`)
    console.log(`   Description: ${l.description.substring(0, 100)}...`)
  })

  // 3. Group by location
  console.log('\n📍 Listings by Location:')
  const locations = await prisma.listing.groupBy({
    by: ['location'],
    _count: { location: true },
    orderBy: { _count: { location: 'desc' } },
    take: 10
  })

  locations.forEach(loc => {
    console.log(`   ${loc.location}: ${loc._count.location} listings`)
  })
}

main()
  .catch(e => {
    console.error('❌ Error:', e.message)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
