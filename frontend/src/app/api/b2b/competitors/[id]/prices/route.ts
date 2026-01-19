import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'

// GET /api/b2b/competitors/[id]/prices -> latest price history
export async function GET(_req: Request, context: { params: { id: string } }) {
  const { id } = context.params
  if (!id) return NextResponse.json({ error: 'id required' }, { status: 400 })
  try {
    const competitor = await prisma.competitor.findUnique({ where: { id } })
    if (!competitor) return NextResponse.json({ error: 'not found' }, { status: 404 })
    const prices = await prisma.competitorPrice.findMany({
      where: { competitorId: id },
      orderBy: { capturedAt: 'desc' },
      take: 60
    })
    return NextResponse.json({ competitor, prices })
  } catch (e) {
    console.error('Fetch competitor prices error', e)
    return NextResponse.json({ error: 'internal error' }, { status: 500 })
  }
}
