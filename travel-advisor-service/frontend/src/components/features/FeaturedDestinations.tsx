"use client"

import Image from "next/image"
import Link from "next/link"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { MapPin } from "lucide-react"
import { CardItem } from "@/types/ui"
import { normalizeImageUrl } from "@/lib/adapters/destinationAdapter"

interface FeaturedDestinationsProps {
  items: CardItem[]
  title?: string
  subtitle?: string
}

const FeaturedDestinations: React.FC<FeaturedDestinationsProps> = ({ 
  items,
  title = "Các điểm đến nổi bật",
  subtitle = "Khám phá các tỉnh thành và địa điểm du lịch tuyệt vời"
}) => {
  if (items.length === 0) {
    return (
      <section className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-900">
            Chưa có điểm đến nào
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Dữ liệu đang được cập nhật...
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <div className="text-center mb-12">
        <h2 className="text-3xl font-bold text-gray-900">
          {title}
        </h2>
        <p className="mt-4 text-lg text-gray-600">
          {subtitle}
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
        {items.map((item) => {
          const safeImage = item.imageSrc
          
          // Xác định detail link dựa vào typenormalizeImageUrl(
          const detailLink = item.type === 'PROVINCE' 
            ? `/destinations/${item.slug}` 
            : `/spots/${item.slug}`

          return (
            <Card key={item.id} className="overflow-hidden flex flex-col h-full group">
              {/* Image Section */}
              <div className="relative w-full h-56">
                <Image
                  src={safeImage}
                  alt={item.title}
                  fill
                  className="object-cover transition-transform duration-300"
                  
                  priority={false}
                  unoptimized={true}
                />
                {/* Badge loại (Province/Spot) */}
                <span className={`absolute top-2 left-2 text-white text-xs px-2 py-1 rounded shadow ${
                  item.type === 'PROVINCE' ? 'bg-blue-600' : 'bg-green-600'
                }`}>
                  {item.badge}
                </span>
              </div>

              {/* Content Section */}
              <CardHeader className="pb-2">
                <CardTitle className="truncate">{item.title}</CardTitle>
                <CardDescription className="flex items-start text-xs line-clamp-2 min-h-10">
                  <MapPin className="h-3 w-3 mr-1 mt-0.5 shrink-0" />
                  {item.subtitle}
                </CardDescription>
              </CardHeader>

              <CardContent className="py-2 grow">
                <div className="flex justify-between items-center bg-gray-50 p-2 rounded-lg">
                  {/* Thông tin chính (Best time cho Province, Cost cho Spot) */}
                  <span className="font-semibold text-sm text-gray-800">
                    {item.infoPrimary}
                  </span>
                  
                  {/* Thông tin phụ (Rating cho Spot, không có cho Province) */}
                  {item.infoSecondary && (
                    <span className="text-sm text-yellow-600 font-medium">
                      {item.infoSecondary}
                    </span>
                  )}
                </div>
              </CardContent>

              <CardFooter className="pt-2">
                <Link href={detailLink} className="w-full">
                  <Button className="w-full" variant="outline">
                    Xem chi tiết
                  </Button>
                </Link>
              </CardFooter>
            </Card>
          )
        })}
      </div>
    </section>
  )
}

export default FeaturedDestinations
