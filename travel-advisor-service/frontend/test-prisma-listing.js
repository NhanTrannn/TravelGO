// Simple test: Query Listing table directly
const { PrismaClient } = require('@prisma/client')
const prisma = new PrismaClient()

async function test() {
  try {
    const listings = await prisma.listing.findMany({
      where: {
        location: {
          contains: "Đà Lạt"
        }
      },
      take: 3
    })
    
    console.log(`Found ${listings.length} listings:`)
    listings.forEach(l => {
      console.log(`- ${l.title} | ${l.location} | ${l.price}đ`)
    })
  } catch (e) {
    console.error('Error:', e.message)
  } finally {
    await prisma.$disconnect()
  }
}

test()
