import { NextResponse } from "next/server"
import prisma from "@/lib/prisma"
import { getServerSession } from "next-auth/next"
import { authOptions } from "../auth/[...nextauth]/route"

export async function POST(request: Request) {
  const session = await getServerSession(authOptions)
  if (!session || !session.user?.email) {
    return new NextResponse("Chưa được xác thực", { status: 401 })
  }
  const currentUser = await prisma.user.findUnique({
    where: { email: session.user.email }
  });
  if (!currentUser) {
     return new NextResponse("Người dùng không hợp lệ", { status: 401 })
  }
  const body = await request.json()
  const { listingId, startDate, endDate, totalPrice } = body
  if (!listingId || !startDate || !endDate || !totalPrice) {
    return new NextResponse("Thiếu thông tin", { status: 400 })
  }
  try {
    const booking = await prisma.booking.create({
      data: {
        listingId: listingId,
        userId: currentUser.id,
        startDate: new Date(startDate),
        endDate: new Date(endDate),
        totalPrice: totalPrice,
      },
    })
    return NextResponse.json(booking)
  } catch (error) {
    console.error("BOOKING_POST_ERROR", error)
    return new NextResponse("Lỗi máy chủ nội bộ", { status: 500 })
  }
}
