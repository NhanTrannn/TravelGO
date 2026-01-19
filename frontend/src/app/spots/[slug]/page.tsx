/**
 * Spot Detail Page - Hiển thị thông tin chi tiết về 1 địa điểm
 * Route: /spots/[slug]
 */

import Image from 'next/image'
import { notFound } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { MapPin, Star, DollarSign, Tag } from 'lucide-react'
import Link from 'next/link'
import { SpotRaw } from '@/types/raw'
import { normalizeImageUrl } from '@/lib/adapters/destinationAdapter'

type PageProps = {
  params: Promise<{ slug: string }>
}

// Fetch spot detail từ Python backend
async function fetchSpotDetail(slug: string): Promise<SpotRaw | null> {
  try {
    const PYTHON_BACKEND = process.env.PYTHON_BACKEND_URL || process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL || 'http://localhost:8001'
    const res = await fetch(`${PYTHON_BACKEND}/api/spots/${slug}`, {
      cache: 'no-store',
      headers: { 'Accept': 'application/json' }
    })

    if (!res.ok) {
      console.error(`Failed to fetch spot detail: ${res.statusText}`)
      return null
    }

    const data = await res.json()
    return data.spot || null
  } catch (error) {
    console.error('Error fetching spot detail:', error)
    return null
  }
}

export default async function SpotDetailPage({ params }: PageProps) {
  const { slug } = await params
  const spot = await fetchSpotDetail(slug)

  if (!spot) {
    notFound()
  }

  const safeImage = normalizeImageUrl(spot.image)

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <section className="relative h-[400px] w-full">
        <Image
          src={safeImage}
          alt={spot.name}
          fill
          className="object-cover"
          priority
          unoptimized
        />
        <div className="absolute inset-0 bg-linear-to-t from-black/60 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-8 text-white">
          <div className="container mx-auto">
            <h1 className="text-4xl md:text-5xl font-bold mb-2">{spot.name}</h1>
            <div className="flex items-center gap-4 text-lg">
              <span className="flex items-center gap-1">
                <MapPin className="h-5 w-5" />
                {spot.address}
              </span>
              {spot.rating > 0 && (
                <span className="flex items-center gap-1">
                  <Star className="h-5 w-5 fill-yellow-400 text-yellow-400" />
                  {spot.rating.toFixed(1)} ({spot.reviews_count} đánh giá)
                </span>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Main Content */}
      <section className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Main Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Description */}
            <Card>
              <CardHeader>
                <CardTitle>Giới thiệu</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose max-w-none">
                  {spot.description_full ? (
                    <div
                      dangerouslySetInnerHTML={{ 
                        __html: spot.description_full.replace(/\n/g, '<br />') 
                      }}
                      className="text-gray-700 leading-relaxed"
                    />
                  ) : spot.description_short ? (
                    <p className="text-gray-700 leading-relaxed">{spot.description_short}</p>
                  ) : (
                    <p className="text-gray-500 italic">Chưa có mô tả chi tiết</p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Tags */}
            {spot.tags && spot.tags.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Tag className="h-5 w-5 text-blue-600" />
                    Thẻ tag
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {spot.tags.map((tag, idx) => (
                      <span key={idx} className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm">
                        {tag}
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
                {/* Cost */}
                <div className="flex items-start gap-3">
                  <DollarSign className="h-5 w-5 text-green-600 mt-0.5 shrink-0" />
                  <div>
                    <p className="font-semibold text-sm text-gray-500">Giá vé</p>
                    <p className="text-gray-900 font-semibold">{spot.cost}</p>
                  </div>
                </div>

                {/* Rating */}
                {spot.rating > 0 && (
                  <div className="flex items-start gap-3">
                    <Star className="h-5 w-5 text-yellow-500 mt-0.5 shrink-0" />
                    <div>
                      <p className="font-semibold text-sm text-gray-500">Đánh giá</p>
                      <p className="text-gray-900 font-semibold">
                        {spot.rating.toFixed(1)}/5.0
                      </p>
                      <p className="text-sm text-gray-600">{spot.reviews_count} lượt đánh giá</p>
                    </div>
                  </div>
                )}

                {/* Province */}
                <div className="flex items-start gap-3">
                  <MapPin className="h-5 w-5 text-blue-600 mt-0.5 shrink-0" />
                  <div>
                    <p className="font-semibold text-sm text-gray-500">Địa chỉ</p>
                    <p className="text-gray-900">{spot.address}</p>
                  </div>
                </div>

                {/* Location */}
                {spot.latitude && spot.longitude && (
                  <div className="mt-4">
                    <p className="text-sm text-gray-500 mb-2">Tọa độ</p>
                    <p className="text-xs text-gray-600">
                      {spot.latitude.toFixed(6)}, {spot.longitude.toFixed(6)}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Action Buttons */}
            <div className="space-y-3">
              {spot.url && (
                <Link href={spot.url} target="_blank" className="block">
                  <Button variant="outline" className="w-full">
                    Xem nguồn gốc
                  </Button>
                </Link>
              )}
              <Link href={`/destinations/${spot.province_id}`}>
                <Button variant="default" className="w-full">
                  Xem tỉnh {spot.province_id.replace(/-/g, ' ')}
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
