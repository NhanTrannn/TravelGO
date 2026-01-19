import { NextResponse } from "next/server"
import prisma from "@/lib/prisma"
import { getServerSession } from "next-auth/next"
import { authOptions } from "../auth/[...nextauth]/route"

export async function POST(request: Request) {
  const session = await getServerSession(authOptions)

  if (!session || !session.user?.email) {
    return new NextResponse("Chưa được xác thực", { status: 401 })
  }

  const body = await request.json()
  const { title, description, imageSrc, location, price } = body

  if (!title || !description || !imageSrc || !location || !price) {
    return new NextResponse("Thiếu thông tin", { status: 400 })
  }

  const userEmail = session.user.email;
  const user = await prisma.user.findUnique({
    where: { email: userEmail },
  });

  if (!user) {
    return new NextResponse("Người dùng không tồn tại", { status: 404 })
  }

  try {
    const listing = await prisma.listing.create({
      data: {
        title,
        description,
        imageSrc,
        location,
        price: parseInt(price, 10),
        userId: user.id,
      },
    })
    return NextResponse.json(listing)
  } catch (error) {
    console.error("LISTING_POST_ERROR", error)
    return new NextResponse("Lỗi máy chủ nội bộ", { status: 500 })
  }
}
