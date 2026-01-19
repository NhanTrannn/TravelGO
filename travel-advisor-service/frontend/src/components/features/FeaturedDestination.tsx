"use client" // Dùng 'use client' vì chúng ta sẽ dùng Next/Image

import Image from "next/image"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { MapPin, Star } from "lucide-react"

import Link from "next/link"
// Type cho Listing
export type Listing = {
  id: string;
  title: string;
  description: string;
  imageSrc: string;
  location: string;
  price: number;
  createdAt: string;
}

interface FeaturedDestinationsProps {
  listings: Listing[]
}

const normalizeImageUrl = (src?: string): string => {
  const placeholder = 'https://placehold.co/1200x800?text=No+Image';
  if (!src) return placeholder;
  const s = src.trim();
  if (s.startsWith('http://') || s.startsWith('https://') || s.startsWith('data:')) return s;
  if (s.startsWith('/')) return s;
  return placeholder;
};

const FeaturedDestinations: React.FC<FeaturedDestinationsProps> = ({ listings }) => {
  if (listings.length === 0) {
    return (
      <section className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-900">
            Chưa có điểm đến nào
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Hãy là người đầu tiên tạo một listing!
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <div className="text-center mb-12">
        <h2 className="text-3xl font-bold text-gray-900">
          Các điểm đến nổi bật
        </h2>
        <p className="mt-4 text-lg text-gray-600">
          Khám phá những địa điểm được cộng đồng tạo ra.
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
        {listings.map((listing) => (
          <Card key={listing.id} className="overflow-hidden">
            <div className="relative w-full h-56">
              <Image
                src={normalizeImageUrl(listing.imageSrc)}
                alt={`Ảnh ${listing.title}`}
                fill
                style={{ objectFit: 'cover' }}
                sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                priority={false}
                unoptimized={false}
              />
            </div>
            <CardHeader>
              <CardTitle>{listing.title}</CardTitle>
              <CardDescription className="flex items-center pt-1">
                <MapPin className="h-4 w-4 mr-1 text-gray-500" />
                {listing.location}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex justify-between items-center">
                <div className="flex items-center">
                  <Star className="h-5 w-5 text-yellow-400 fill-yellow-400 mr-1" />
                  <span className="font-semibold">Mới</span>
                </div>
                <div>
                  <span className="text-lg font-bold text-blue-600">
                    {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(listing.price)}
                  </span>
                  <span className="text-sm text-gray-500"> /đêm</span>
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Link href={`/listings/${listing.id}`} className="w-full">
                <Button className="w-full" variant="outline">
                  Xem chi tiết
                </Button>
              </Link>
            </CardFooter>
          </Card>
        ))}
      </div>
    </section>
  )
}

export default FeaturedDestinations