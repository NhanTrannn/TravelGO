import { NextRequest, NextResponse } from "next/server";
import prisma from "@/lib/prisma";

// GET /api/bookings/[bookingId]
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ bookingId: string }> }
) {
  const { bookingId } = await params;

  if (!bookingId) return new NextResponse("Bad Request", { status: 400 });

  const booking = await prisma.booking.findUnique({
    where: { id: bookingId },
    include: { listing: true },
  });

  if (!booking) return new NextResponse("Not Found", { status: 404 });
  return NextResponse.json(booking);
}

// PATCH /api/bookings/[bookingId]
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ bookingId: string }> }
) {
  const { bookingId } = await params;

  if (!bookingId) return new NextResponse("Bad Request", { status: 400 });

  const body = await request.json();

  const updated = await prisma.booking.update({
    where: { id: bookingId },
    // giữ y như bạn: ép kiểu để tránh mismatch transient
    data: { status: body.status as string } as any,
  });

  return NextResponse.json(updated);
}
