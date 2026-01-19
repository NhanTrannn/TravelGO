import { NextRequest, NextResponse } from "next/server";

const PYTHON_BACKEND = process.env.BACKEND_ORIGIN || "http://localhost:8001";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: slug } = await params;

  const { searchParams } = new URL(req.url);
  const limit = Number(searchParams.get("limit") || "20");
  const offset = Number(searchParams.get("offset") || "0");

  try {
    const url = `${PYTHON_BACKEND}/api/spots/by-province?slug=${encodeURIComponent(
      slug
    )}&limit=${limit}&offset=${offset}`;

    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`Backend ${res.status}`);

    const data = await res.json();
    const spots = Array.isArray(data?.spots) ? data.spots : [];
    return NextResponse.json({ spots, total: data?.total || 0, province_id: slug, limit, offset });
  } catch (err) {
    console.error("[API] Spots by province error:", err);
    return NextResponse.json(
      { spots: [], total: 0, province_id: slug, limit, offset, isFallback: true },
      { status: 200 }
    );
  }
}
