import { NextResponse } from 'next/server'

// Province metadata
const PROVINCE_METADATA = {
  'da-lat': {
    name: 'Đà Lạt',
    description: 'Thành phố ngàn hoa với khí hậu mát mẻ quanh năm, nổi tiếng với Thung lũng Tình Yêu, Hồ Xuân Hương và những đồi chè xanh mướt.',
    bestTime: 'Tháng 11 - 3'
  },
  // 'ha-noi': {
  //   name: 'Hà Nội',
  //   description: 'Thủ đô ngàn năm văn hiến với Hồ Hoàn Kiếm, Văn Miếu Quốc Tử Giám, Phố Cổ và ẩm thực đường phố đặc sắc.',
  //   bestTime: 'Tháng 10 - 4'
  // },
  // 'da-nang': {
  //   name: 'Đà Nẵng',
  //   description: 'Thành phố đáng sống với Cầu Rồng, Bà Nà Hills, bãi biển Mỹ Khê tuyệt đẹp và gần Hội An cổ kính.',
  //   bestTime: 'Tháng 2 - 8'
  // },
  // 'quang-ninh': {
  //   name: 'Quảng Ninh',
  //   description: 'Vịnh Hạ Long kỳ quan thế giới, hang Sơn Đoòng, Yên Tử linh thiêng và những bãi biển hoang sơ.',
  //   bestTime: 'Tháng 9 - 4'
  // },
  // 'ba-ria-vung-tau': {
  //   name: 'Bà Rịa - Vũng Tàu',
  //   description: 'Bãi biển Vũng Tàu gần Sài Gòn, tượng Chúa Ki-tô, núi Thánh Giá và hải sản tươi ngon.',
  //   bestTime: 'Quanh năm'
  // },
  // 'binh-thuan': {
  //   name: 'Bình Thuận',
  //   description: 'Mũi Né với đồi cát bay, làng chài đẹp như tranh vẽ, resort view biển và thể thao lướt ván.',
  //   bestTime: 'Tháng 11 - 4'
  // },
  // 'gia-lai': {
  //   name: 'Gia Lai',
  //   description: 'Tây Nguyên hùng vĩ với đồi chè Chư Sê, biển Hồ Pleiku, làng Kon K\'Tu và văn hóa Gong độc đáo.',
  //   bestTime: 'Tháng 10 - 3'
  // },
  // 'quang-ngai': {
  //   name: 'Quảng Ngãi',
  //   description: 'Đảo Lý Sơn với mùa tỏi tươi, di tích lịch sử Sơn Mỹ, bãi biển Mỹ Khê và ẩm thực miền Trung.',
  //   bestTime: 'Tháng 3 - 8'
  // },
  // 'ninh-thuan': {
  //   name: 'Ninh Thuận',
  //   description: 'Vườn nho Thái An, tháp Chăm cổ, bãi biển Vĩnh Hy hoang sơ và ẩm thực Chăm độc đáo.',
  //   bestTime: 'Tháng 1 - 8'
  // }
} as const

const DEFAULT_IMAGE = 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800'
const PYTHON_BACKEND = process.env.PYTHON_BACKEND_URL || process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL || 'http://localhost:8001'

// Types
type FeaturedProvince = {
  province_id: string
  name?: string
  description?: string
  image?: string | null
  spot_count?: number
}

type RecommendationItem = {
  id?: string
  name?: string
  description?: string
  imageSrc?: string | null
  bestTime?: string
  tags?: unknown
  region?: string
  spotCount?: number
}

// --- GET Handler: Lấy danh sách Tỉnh (Hỗ trợ phân trang & Fallback) ---
export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url)
    const page = searchParams.get('page') || '1'
    const limit = searchParams.get('limit') || '20'

    console.log(`🔗 Fetching provinces from backend: ${PYTHON_BACKEND}/api/provinces/all?page=${page}`)

    let response = await fetch(`${PYTHON_BACKEND}/api/provinces/all?page=${page}&limit=${limit}`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(8000) // 8s timeout
    })

    // Nếu API all lỗi, thử fallback sang featured
    if (!response.ok) {
      console.warn('⚠️ /api/provinces/all failed, falling back to /api/provinces/featured')
      response = await fetch(`${PYTHON_BACKEND}/api/provinces/featured`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(5000)
      })
      
      if (!response.ok) {
        throw new Error(`Backend Error: ${response.statusText}`)
      }
    }

    const data = await response.json()
    const provinces = Array.isArray(data?.provinces) ? (data.provinces as FeaturedProvince[]) : []
    
    // Map dữ liệu & Enrich metadata
    const destinations = provinces.map((province: FeaturedProvince) => {
      const meta = PROVINCE_METADATA[province?.province_id as keyof typeof PROVINCE_METADATA]
      return {
        id: province?.province_id,
        type: 'province', // Đánh dấu loại để UI render đúng
        province_id: province?.province_id,
        name: meta?.name || province?.name || 'Không tên',
        description: meta?.description || province?.description || 'Một điểm đến thú vị đang chờ bạn khám phá.',
        imageSrc: province?.image || DEFAULT_IMAGE,
        meta: {
            bestTime: meta?.bestTime || 'Quanh năm',
            region: 'Vietnam'
        },
        spotCount: typeof province?.spot_count === 'number' ? province.spot_count : 0
      }
    })

    return NextResponse.json({
      destinations,
      total: data.total || destinations.length,
      has_more: data.has_more || false,
      source: 'backend-provinces'
    })

  } catch (error) {
    console.error('[GET] Destinations Error:', error)
    
    // Fallback tĩnh (Static Data)
    const fallbackDestinations = Object.entries(PROVINCE_METADATA).slice(0, 9).map(([id, data]) => ({
      id,
      type: 'province',
      province_id: id,
      name: data.name,
      description: data.description,
      imageSrc: DEFAULT_IMAGE,
      meta: { bestTime: data.bestTime },
      spotCount: 0
    }))

    return NextResponse.json({
      destinations: fallbackDestinations,
      total: fallbackDestinations.length,
      source: 'static-fallback',
      isFallback: true
    })
  }
}

// --- POST Handler: Lấy Recommendation thông minh từ AI ---
type RecommendationRequest = {
  mode?: 'random' | 'personalized'
  preferences?: Record<string, unknown> | null
  limit?: number
}

export async function POST(req: Request) {
  try {
    const body = (await req.json().catch(() => ({}))) as Partial<RecommendationRequest>
    const { mode = 'random', preferences = null, limit = 9 } = body || {}

    const res = await fetch(`${PYTHON_BACKEND}/api/recommend-destinations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, preferences, limit }),
      cache: 'no-store',
      signal: AbortSignal.timeout(15000) // 15s timeout vì AI chạy lâu
    })

    if (!res.ok) {
      throw new Error(`Python backend error: ${res.status}`)
    }

    const data = await res.json()
    const rawList = Array.isArray(data?.destinations) ? (data.destinations as RecommendationItem[]) : []
    
    const destinations = rawList.map((item: RecommendationItem) => ({
      id: item?.id || 'unknown',
      type: 'spot', // AI thường trả về cả spot lẫn province, nhưng tạm để spot hoặc check logic
      name: item?.name || 'Điểm đến bí ẩn',
      description: item?.description || 'Chưa có mô tả',
      imageSrc: item?.imageSrc || DEFAULT_IMAGE,
      meta: {
          bestTime: item?.bestTime || 'Quanh năm',
          rating: 4.5, // Giả lập rating nếu AI không trả về
          address: item?.region || ''
      },
      tags: Array.isArray(item?.tags) ? item.tags : [],
      spotCount: typeof item?.spotCount === 'number' ? item.spotCount : 0
    }))

    return NextResponse.json({
      destinations,
      total: destinations.length,
      notes: data?.notes || '',
      source: data?.source || 'ai-recommendation',
      isFallback: false
    })

  } catch (error) {
    console.error('[POST] Recommendation Error:', error)
    return NextResponse.json({
      destinations: [
        { id: 'da-nang', type: 'province', name: 'Đà Nẵng (Mặc định)', description: 'Thành phố biển xinh đẹp (Dữ liệu dự phòng)', imageSrc: DEFAULT_IMAGE, meta: { bestTime: 'Quanh năm' } },
        { id: 'ha-noi', type: 'province', name: 'Hà Nội (Mặc định)', description: 'Thủ đô văn hiến (Dữ liệu dự phòng)', imageSrc: DEFAULT_IMAGE, meta: { bestTime: 'Quanh năm' } }
      ],
      total: 2,
      notes: 'Hệ thống gợi ý đang bảo trì hoặc kết nối chậm.',
      source: 'error-fallback',
      isFallback: true
    }, { status: 200 })
  }
}