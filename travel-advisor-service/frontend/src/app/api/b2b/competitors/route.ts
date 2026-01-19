import { NextResponse } from 'next/server'
import prisma from '@/lib/prisma'

// POST /api/b2b/competitors  -> register a competitor to monitor
// GET  /api/b2b/competitors  -> list competitors

export async function POST(req: Request) {
  try {
    const body = await req.json()
    const { name, url, location } = body
    if (!name || !url) {
      return NextResponse.json({ error: 'name and url required' }, { status: 400 })
    }
    const created = await prisma.competitor.create({
      data: {
        name,
        url,
        location: location || null
      }
    })
    return NextResponse.json(created)
  } catch (e) {
    console.error('Create competitor error', e)
    return NextResponse.json({ error: 'internal error' }, { status: 500 })
  }
}

export async function GET() {
  try {
    const items = await prisma.competitor.findMany({
      where: { active: true },
      orderBy: { createdAt: 'desc' },
      take: 50
    })
    return NextResponse.json(items)
  } catch (e) {
    console.error('List competitors error', e)
    return NextResponse.json({ error: 'internal error' }, { status: 500 })
  }
}
