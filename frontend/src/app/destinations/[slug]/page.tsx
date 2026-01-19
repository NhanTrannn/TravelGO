/**
 * Province Detail Page - Hiển thị thông tin chi tiết về 1 tỉnh thành
 * Route: /destinations/[slug]
 */

import Image from 'next/image'
import { notFound } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { MapPin, Calendar, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { ProvinceRaw, SpotRaw } from '@/types/raw'
import { normalizeImageUrl } from '@/lib/adapters/destinationAdapter'

type PageProps = {
  params: Promise<{ slug: string }>
}

// Fetch province info từ Python backend
async function fetchProvinceInfo(slug: string): Promise<ProvinceRaw | null> {
  try {
    const PYTHON_BACKEND = process.env.PYTHON_BACKEND_URL || process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL || 'http://localhost:8001'
    const res = await fetch(`${PYTHON_BACKEND}/api/provinces/${slug}/info`, {
      cache: 'no-store',
      headers: { 'Accept': 'application/json' }
    })

    if (!res.ok) {
      console.error(`Failed to fetch province info: ${res.statusText}`)
      return null
    }

    const data = await res.json()
    return data.province || null
  } catch (error) {
    console.error('Error fetching province info:', error)
    return null
  }
}

// Fetch spots thuộc province
async function fetchProvinceSpots(slug: string, limit = 12): Promise<SpotRaw[]> {
  try {
    const PYTHON_BACKEND = process.env.PYTHON_BACKEND_URL || process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL || 'http://localhost:8001'
    const res = await fetch(`${PYTHON_BACKEND}/api/spots/by-province?slug=${slug}&limit=${limit}`, {
      cache: 'no-store',
      headers: { 'Accept': 'application/json' }
    })

    if (!res.ok) return []

    const data = await res.json()
    return data.spots || []
  } catch (error) {
    console.error('Error fetching province spots:', error)
    return []
  }
}

export default async function ProvinceDetailPage({ params }: PageProps) {
  const { slug } = await params
  const [province, spots] = await Promise.all([
    fetchProvinceInfo(slug),
    fetchProvinceSpots(slug)
  ])

  if (!province) {
    notFound()
  }

  const safeImage = normalizeImageUrl(province.image)
  const regionLabels: Record<string, string> = {
    north: 'Miền Bắc',
    central: 'Miền Trung',
    south: 'Miền Nam',
    highlands: 'Tây Nguyên'
  }

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <section className="relative h-[400px] w-full">
        <Image
          src={safeImage}
          alt={province.name}
          fill
          className="object-cover"
          priority
          unoptimized
        />
        <div className="absolute inset-0 bg-linear-to-t from-black/60 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-8 text-white">
          <div className="container mx-auto">
            <h1 className="text-4xl md:text-5xl font-bold mb-2">{province.name}</h1>
            <p className="text-xl">{province.name_en}</p>
          </div>
        </div>
      </section>

      {/* Main Content */}
      <section className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Main Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Overview Card */}
            <Card>
              <CardHeader>
                <CardTitle>Giới thiệu</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-700 leading-relaxed">{province.description}</p>
              </CardContent>
            </Card>

            {/* Highlights */}
            {province.highlights && province.highlights.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-yellow-500" />
                    Điểm nổi bật
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {province.highlights.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-blue-600 mt-1">•</span>
                        <span className="text-gray-700">{item}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {/* Cuisine */}
            {province.cuisine && province.cuisine.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>🍜 Ẩm thực đặc sản</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {province.cuisine.map((item, idx) => (
                      <span key={idx} className="bg-orange-100 text-orange-800 px-3 py-1 rounded-full text-sm">
                        {item}
                      </span>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column - Meta Info */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Thông tin</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-start gap-3">
                  <MapPin className="h-5 w-5 text-blue-600 mt-0.5 shrink-0" />
                  <div>
                    <p className="font-semibold text-sm text-gray-500">Vùng miền</p>
                    <p className="text-gray-900">{province.region_detail || regionLabels[province.region]}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Calendar className="h-5 w-5 text-green-600 mt-0.5 shrink-0" />
                  <div>
                    <p className="font-semibold text-sm text-gray-500">Thời điểm đẹp nhất</p>
                    <p className="text-gray-900">{province.best_time}</p>
                    {province.best_time_detail && (
                      <p className="text-sm text-gray-600 mt-1">{province.best_time_detail}</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {province.url && (
              <Link href={province.url} target="_blank">
                <Button variant="outline" className="w-full">
                  Xem nguồn gốc
                </Button>
              </Link>
            )}
          </div>
        </div>

        {/* Spots Section */}
        {spots.length > 0 && (
          <section className="mt-12">
            <h2 className="text-3xl font-bold mb-6">Địa điểm tại {province.name}</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {spots.map((spot) => (
                <Link key={spot.id} href={`/spots/${spot.id}`}>
                  <Card className="overflow-hidden hover:shadow-lg transition-shadow h-full">
                    <div className="relative h-48 w-full">
                      <Image
                        src={normalizeImageUrl(spot.image)}
                        alt={spot.name}
                        fill
                        className="object-cover"
                        unoptimized={true}
                      />
                    </div>
                    <CardHeader className="p-4">
                      <CardTitle className="text-lg line-clamp-2">{spot.name}</CardTitle>
                      <CardDescription className="text-sm line-clamp-2">{spot.address}</CardDescription>
                    </CardHeader>
                    <CardContent className="px-4 pb-4">
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-green-600 font-semibold">{spot.cost}</span>
                        {spot.rating > 0 && (
                          <span className="text-yellow-600">⭐ {spot.rating.toFixed(1)}</span>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          </section>
        )}
      </section>
    </main>
  )
}
