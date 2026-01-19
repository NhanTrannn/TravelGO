import prisma from "@/lib/prisma"
import { getServerSession } from "next-auth/next"
import Image from "next/image"
import { authOptions } from "../api/auth/[...nextauth]/route"

export default async function TripsPage() {
  const session = await getServerSession(authOptions)
  if (!session?.user?.email) return <div className="p-10 text-center">Vui lòng đăng nhập</div>

  const user = await prisma.user.findUnique({ where: { email: session.user.email } })
  const bookings = await prisma.booking.findMany({
    where: { userId: user?.id },
    include: { listing: true },
    orderBy: { createdAt: 'desc' },
  })

  return (
    <div className="container mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold mb-6">Chuyến đi của tôi</h1>
      <div className="space-y-4">
        {bookings.map((booking: { id: string; startDate: Date; endDate: Date; totalPrice: number; listing: { imageSrc: string; title: string }; status?: string }) => (
          <div key={booking.id} className="flex border rounded-lg overflow-hidden bg-white shadow-sm">
            <div className="relative w-48 h-32">
              <Image src={booking.listing.imageSrc} alt="img" fill style={{ objectFit: 'cover' }} />
            </div>
            <div className="p-4 flex-1 flex justify-between items-center">
              <div>
                <h3 className="font-bold text-lg">{booking.listing.title}</h3>
                <p className="text-gray-500">{new Date(booking.startDate).toLocaleDateString()} - {new Date(booking.endDate).toLocaleDateString()}</p>
                <p className="font-semibold mt-1">{new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(booking.totalPrice)}</p>
              </div>
              <div className="mr-4">
                {booking.status === 'PAID' ? (
                  <span className="flex items-center text-green-600 font-bold gap-1 bg-green-50 px-3 py-1 rounded-full">
                    ✓ Đã thanh toán
                  </span>
                ) : (
                  <span className="flex items-center text-orange-600 font-bold gap-1 bg-orange-50 px-3 py-1 rounded-full">
                    ⏳ Chờ thanh toán
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
