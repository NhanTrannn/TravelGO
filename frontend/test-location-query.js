// Quick test to check what locations exist in DB
const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();

async function testLocationQuery() {
  try {
    // 1. Count total listings
    const total = await prisma.listing.count();
    console.log(`📊 Total listings: ${total}`);

    // 2. Get distinct locations (sample first 20)
    const locations = await prisma.listing.findMany({
      select: { location: true },
      distinct: ['location'],
      take: 20
    });
    console.log('\n📍 Sample locations:');
    locations.forEach(l => console.log(`  - ${l.location}`));

    // 3. Test search for "Hà Nội"
    const hanoiExact = await prisma.listing.count({
      where: { location: { contains: 'Hà Nội' } }
    });
    console.log(`\n🔍 "Hà Nội" exact: ${hanoiExact} results`);

    // 4. Test search for "Đống Đa Hà Nội"
    const dongDa = await prisma.listing.count({
      where: { location: { contains: 'Đống Đa Hà Nội' } }
    });
    console.log(`🔍 "Đống Đa Hà Nội": ${dongDa} results`);

    // 5. Test flexible search (case insensitive, partial match)
    const hanoiFlexible = await prisma.listing.count({
      where: {
        location: {
          contains: 'ha noi',
          mode: 'insensitive'
        }
      }
    });
    console.log(`🔍 "ha noi" (case-insensitive): ${hanoiFlexible} results`);

    // 6. Show sample Hà Nội hotels
    const hanoiHotels = await prisma.listing.findMany({
      where: {
        location: {
          contains: 'nội',
          mode: 'insensitive'
        }
      },
      select: { id: true, title: true, location: true, price: true },
      take: 5
    });
    console.log('\n🏨 Sample Hà Nội hotels:');
    hanoiHotels.forEach(h => {
      console.log(`  - ${h.title} (${h.location}) - ${h.price.toLocaleString()} VND`);
    });

  } catch (error) {
    console.error('❌ Error:', error.message);
  } finally {
    await prisma.$disconnect();
  }
}

testLocationQuery();
