import { NextResponse } from "next/server"
import prisma from "@/lib/prisma"

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function GET(request: Request, { params }: any) {
  if (!params.bookingId) return new NextResponse("Bad Request", { status: 400 })
  const booking = await prisma.booking.findUnique({
    where: { id: params.bookingId },
    include: { listing: true },
  })
  if (!booking) return new NextResponse("Not Found", { status: 404 })
  return NextResponse.json(booking)
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function PATCH(request: Request, { params }: any) {
  if (!params.bookingId) return new NextResponse("Bad Request", { status: 400 })
  const body = await request.json()
  const updated = await prisma.booking.update({
    where: { id: params.bookingId },
    // Cast to any to avoid transient type mismatch if client types are stale
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    data: { status: body.status as string } as any,
  })
  return NextResponse.json(updated)
}
