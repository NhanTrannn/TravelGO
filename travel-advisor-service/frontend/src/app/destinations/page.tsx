"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { MapPin, Loader2, Star, Calendar, ArrowDownCircle } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

// Unified destination type
type Destination = {
  id: string
  type: 'province' | 'spot'
  name: string
  description: string
  imageSrc: string
  meta: {
    bestTime?: string
    region?: string
    rating?: number
    address?: string
    province_id?: string
  }
}

const DEFAULT_IMAGE = 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800'

export default function DestinationsPage() {
  const [destinations, setDestinations] = useState<Destination[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // State phân trang
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)

  async function fetchDestinations(pageToLoad = 1, isAppend = false) {
    if (isAppend) setLoadingMore(true)
    else setLoading(true)

    try {
      const res = await fetch(`/api/destinations?page=${pageToLoad}&limit=12`)
      const data = await res.json()

      if (data.error) {
        throw new Error(data.error)
      }

      const raw = Array.isArray(data.destinations) ? data.destinations : []
      
      // Normalize data
      const normalized: Destination[] = (raw as Array<Record<string, unknown>>).map((item) => {
        const typeVal = typeof item?.type === 'string' ? item.type : 'province'
        
        const pid = String(item?.province_id ?? item?.id ?? item?.slug ?? 'unknown')
        const name = typeof item?.name === 'string' ? item.name : 'Không tên'
        const description = typeof item?.description === 'string' ? item.description : ''
        
        let imageSrc = DEFAULT_IMAGE
        if (typeof item?.imageSrc === 'string' && item.imageSrc) imageSrc = item.imageSrc
        else if (typeof item?.image === 'string' && item.image) imageSrc = item.image

        const bestTime = typeof item?.bestTime === 'string' ? item.bestTime : (typeVal === 'province' ? 'Quanh năm' : undefined)
        const region = typeof item?.region === 'string' ? item.region : 'Vietnam'
        
        // [FIXED] Sử dụng Record<string, unknown> thay vì any
        const metaObj = item?.meta as Record<string, unknown> | undefined
        const rating = typeof item?.rating === 'number' 
          ? item.rating 
          : (typeof metaObj?.rating === 'number' ? metaObj.rating : 0)

        const address = typeof item?.address === 'string' ? item.address : ''
        const province_id = typeof item?.province_id === 'string' ? item.province_id : ''

        return {
          id: pid,
          type: typeVal as 'province' | 'spot',
          name,
          description,
          imageSrc,
          meta: { bestTime, region, rating, address, province_id }
        }
      })

      if (isAppend) {
        setDestinations(prev => [...prev, ...normalized])
      } else {
        setDestinations(normalized)
      }
      
      if (typeof data.has_more === 'boolean') {
          setHasMore(data.has_more)
      } else {
          setHasMore(normalized.length > 0)
      }

    } catch (err) {
      console.error('Error fetching destinations:', err)
      setError('Không thể tải danh sách điểm đến')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }

  useEffect(() => {
    fetchDestinations(1, false)
  }, [])

  const handleLoadMore = () => {
    const nextPage = page + 1
    setPage(nextPage)
    fetchDestinations(nextPage, true)
  }

  if (loading && destinations.length === 0) {
    return (
      <div className="container mx-auto px-4 py-20">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
            <p className="text-gray-600">Đang tải điểm đến...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error && destinations.length === 0) {
    return (
      <div className="container mx-auto px-4 py-10 text-center">
        <p className="text-red-600">{error}</p>
        <Button variant="outline" className="mt-4" onClick={() => window.location.reload()}>Thử lại</Button>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-20 min-h-screen bg-gray-50">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold text-gray-900">Khám phá Điểm đến</h1>
        <p className="mt-4 text-lg text-gray-600">
          Tìm cảm hứng từ {destinations.length} gợi ý tỉnh thành và địa điểm nổi bật
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8 mb-12">
        <AnimatePresence mode="popLayout">
          {destinations.map((dest) => (
            <motion.div
              key={`${dest.type}-${dest.id}`}
              layout
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <Card className="h-full flex flex-col overflow-hidden hover:shadow-xl transition-shadow duration-300 border-0 bg-white">
                <div className="relative h-56 group overflow-hidden">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={dest.imageSrc}
                    alt={dest.name}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                    onError={(e) => { (e.currentTarget as HTMLImageElement).src = DEFAULT_IMAGE }}
                  />
                  <div className={`absolute top-3 right-3 text-white text-xs px-3 py-1 rounded-full font-medium backdrop-blur-md ${dest.type === 'province' ? 'bg-blue-600/80' : 'bg-green-600/80'}`}>
                    {dest.type === 'province' ? 'Tỉnh thành' : 'Địa điểm'}
                  </div>
                </div>

                <CardHeader className="pb-2">
                  <div className="flex justify-between items-start">
                    <CardTitle className="text-xl font-bold text-gray-800 line-clamp-1" title={dest.name}>
                      {dest.name}
                    </CardTitle>
                  </div>
                  <CardDescription className="flex items-center text-sm font-medium mt-1">
                    {dest.type === 'province' ? (
                      <span className="flex items-center text-blue-600">
                        <Calendar className="h-3.5 w-3.5 mr-1" />
                        {dest.meta.bestTime || 'Quanh năm'}
                      </span>
                    ) : (
                      <span className="flex items-center text-yellow-700">
                        <Star className="h-3.5 w-3.5 mr-1 fill-yellow-500" />
                        {typeof dest.meta.rating === 'number' && dest.meta.rating > 0 ? `${dest.meta.rating}/5` : 'Chưa có đánh giá'}
                      </span>
                    )}
                  </CardDescription>
                </CardHeader>

                <CardContent className="grow">
                  <p className="text-gray-600 text-sm line-clamp-3 leading-relaxed">
                    {dest.description}
                  </p>
                  {dest.type === 'spot' && dest.meta.address && (
                    <div className="mt-3 flex items-start text-xs text-gray-500">
                      <MapPin className="h-3 w-3 mr-1 mt-0.5 shrink-0" />
                      <span className="line-clamp-1">{dest.meta.address}</span>
                    </div>
                  )}
                </CardContent>

                <CardFooter className="pt-0 pb-6 px-6">
                  <Link
                    href={
                      dest.type === 'province'
                        ? `/chat?destination=${encodeURIComponent(dest.id)}`
                        : `/chat?destination=${encodeURIComponent(dest.meta.province_id || '')}&spot=${encodeURIComponent(dest.name)}`
                    }
                    className="w-full"
                  >
                    <Button className={`w-full text-white font-medium py-2 rounded-lg transition-colors ${dest.type === 'province' ? 'bg-blue-900 hover:bg-blue-800' : 'bg-green-700 hover:bg-green-600'}`}>
                      {dest.type === 'province' ? 'Lên lịch trình' : 'Khám phá ngay'}
                    </Button>
                  </Link>
                </CardFooter>
              </Card>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {hasMore && (
        <div className="flex justify-center pb-10">
          <Button 
            onClick={handleLoadMore}
            disabled={loadingMore}
            variant="outline" 
            className="px-8 py-6 rounded-full text-lg border-2 border-blue-600 text-blue-600 hover:bg-blue-50 transition-all shadow-sm hover:shadow-md"
          >
            {loadingMore ? (
                <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Đang tải thêm...
                </>
            ) : (
                <>
                    <ArrowDownCircle className="mr-2 h-6 w-6" />
                    Xem thêm địa điểm
                </>
            )}
          </Button>
        </div>
      )}
      
      {!hasMore && destinations.length > 0 && (
          <div className="text-center pb-10 text-gray-500 italic">
              Đã hiển thị hết danh sách.
          </div>
      )}
    </div>
  )
}