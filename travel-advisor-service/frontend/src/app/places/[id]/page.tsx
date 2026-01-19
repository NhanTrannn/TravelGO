import prisma from "@/lib/prisma"
import Image from "next/image"
import Link from "next/link"
import { Button } from "@/components/ui/Button"

export default async function PlacePage({ params }: { params: { id: string } }) {
  const place = await prisma.place.findUnique({
    where: { id: params.id },
    include: { destination: true },
  })

  if (!place) return <div className="p-10 text-center">Không tìm thấy địa điểm</div>

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let details: any = null
  try {
    if (place.details) details = JSON.parse(place.details)
  } catch {
    // Invalid JSON
  }

  return (
    <div className="container mx-auto px-4 py-10 max-w-4xl">
      {/* Header */}
      <div className="mb-6">
        <Link href={`/destinations/${place.destinationId}`} className="text-blue-600 hover:underline text-sm">
          ← Quay lại {place.destination.name}
        </Link>
      </div>

      <div className="relative w-full h-96 rounded-lg overflow-hidden mb-8">
        <Image src={place.imageSrc} alt={place.name} fill style={{ objectFit: 'cover' }} sizes="100vw" priority />
      </div>

      <h1 className="text-4xl font-bold mb-4">{place.name}</h1>

      <div className="flex items-center gap-4 mb-6">
        <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
          {place.type === 'HOTEL' && 'Khách sạn'}
          {place.type === 'RESTAURANT' && 'Nhà hàng'}
          {place.type === 'ATTRACTION' && 'Điểm vui chơi'}
        </span>
        <span className="text-yellow-600 font-semibold">⭐ {place.rating.toFixed(1)}</span>
        {place.priceRange && <span className="text-gray-600">{place.priceRange}</span>}
      </div>

      <div className="mb-8">
        <h2 className="text-2xl font-semibold mb-4">Mô tả</h2>
        <p className="text-gray-700 leading-relaxed">{place.description}</p>
      </div>

      {/* Specialized Sections */}
      {place.type === 'HOTEL' && details && (
        <div className="bg-gray-50 rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-semibold mb-4">Tiện nghi</h2>
          {details.stars && <p className="mb-2">⭐ {details.stars} sao</p>}
          {details.amenities && (
            <ul className="list-disc pl-6">
              {details.amenities.map((a: string, i: number) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {place.type === 'RESTAURANT' && details && (
        <div className="bg-gray-50 rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-semibold mb-4">Thông tin món ăn</h2>
          {details.cuisine && <p className="mb-2"><strong>Phong cách:</strong> {details.cuisine}</p>}
          {details.signatureDish && <p><strong>Món đặc sản:</strong> {details.signatureDish}</p>}
        </div>
      )}

      {place.type === 'ATTRACTION' && details && (
        <div className="bg-gray-50 rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-semibold mb-4">Thông tin vé & giờ vàng</h2>
          {details.ticketPrice !== undefined && (
            <p className="mb-2">
              <strong>Giá vé:</strong> {details.ticketPrice === 0 ? 'Miễn phí' : `${details.ticketPrice.toLocaleString('vi-VN')} VND`}
            </p>
          )}
          {details.openHours && <p><strong>Giờ mở cửa:</strong> {details.openHours}</p>}
        </div>
      )}

      {/* Map */}
      {place.latitude && place.longitude && (
        <div className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">Vị trí</h2>
          <p className="text-gray-600 mb-4">{place.address}</p>
          <div className="w-full h-80 bg-gray-200 rounded-lg flex items-center justify-center">
            <p className="text-gray-500">Bản đồ tại ({place.latitude.toFixed(4)}, {place.longitude.toFixed(4)})</p>
          </div>
        </div>
      )}

      <div className="flex gap-4">
        <Link href={`/destinations/${place.destinationId}`} className="flex-1">
          <Button variant="outline" className="w-full">
            Khám phá thêm {place.destination.name}
          </Button>
        </Link>
      </div>
    </div>
  )
}
