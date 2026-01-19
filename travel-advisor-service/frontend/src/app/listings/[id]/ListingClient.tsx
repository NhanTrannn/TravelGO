"use client"

import React, { useState } from "react"
import Image from "next/image"
import { MapPin } from "lucide-react"
import { DateRange, RangeKeyDict, Range } from "react-date-range"
import "react-date-range/dist/styles.css"
import "react-date-range/dist/theme/default.css"
import { vi } from 'date-fns/locale'
import { differenceInCalendarDays } from 'date-fns'
import { Button } from "@/components/ui/Button"
import Map from "@/components/ui/Map"
import useLoginModal from "@/hooks/useLoginModal"
import { useRouter } from "next/navigation"
import axios from "axios"
import toast from "react-hot-toast"

// Mở rộng kiểu dữ liệu 'Listing' để bao gồm 'user'
type ListingWithUser = {
  id: string;
  title: string;
  description: string;
  imageSrc: string;
  location: string;
  price: number;
  createdAt: string;
  latitude: number;
  longitude: number;
  sourceUrl?: string | null;
  user: {
    id: string;
    name: string | null;
    email: string | null;
  };
};

type User = {
  id: string;
  name: string | null;
  email: string | null;
};

interface ListingClientProps {
  listing: ListingWithUser;
  currentUser: User | null;
  disabledDates: Date[];
}

const ListingClient: React.FC<ListingClientProps> = ({
  listing,
  currentUser,
  disabledDates
}) => {
  const normalizeImageUrl = (src?: string): string => {
    const placeholder = 'https://placehold.co/1200x800?text=No+Image';
    if (!src) return placeholder;
    const s = src.trim();
    if (s.startsWith('http://') || s.startsWith('https://') || s.startsWith('data:')) return s;
    if (s.startsWith('/')) return s;
    return placeholder;
  };
  const router = useRouter();
  const loginModal = useLoginModal();
  const [isLoading, setIsLoading] = useState(false);
  const [totalPrice, setTotalPrice] = useState(listing.price);
  const [dateRange, setDateRange] = useState<Range[]>([
    {
      startDate: new Date(),
      endDate: new Date(),
      key: "selection",
    },
  ]);

  const onDateChange = (ranges: RangeKeyDict) => {
    setDateRange([ranges.selection]);
    const start = ranges.selection.startDate;
    const end = ranges.selection.endDate;
    if (start && end) {
      const dayCount = differenceInCalendarDays(end, start) + 1;
      if (dayCount && listing.price) {
        setTotalPrice(dayCount * listing.price);
      } else {
        setTotalPrice(listing.price);
      }
    }
  };

  const onCreateBooking = () => {
    if (!currentUser) {
      return loginModal.onOpen();
    }
    setIsLoading(true);
    const loadingToast = toast.loading("Đang xử lý đặt phòng...");
    axios.post("/api/bookings", {
      listingId: listing.id,
      startDate: dateRange[0].startDate,
      endDate: dateRange[0].endDate,
      totalPrice: totalPrice,
    })
    .then((response) => {
      const bookingId = response.data?.id as string | undefined;
      toast.success("Đã tạo đơn! Đang chuyển sang thanh toán...");
      if (bookingId) {
        router.push(`/checkout/${bookingId}`);
      } else {
        router.refresh();
      }
    })
    .catch((error) => {
      toast.error(error.response?.data || "Đã xảy ra lỗi");
    })
    .finally(() => {
      setIsLoading(false);
      toast.dismiss(loadingToast);
    });
  };

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold">{listing.title}</h1>
        <div className="flex items-center text-gray-600 mt-2">
          <MapPin className="h-4 w-4 mr-1" /> {listing.location}
        </div>
        <div className="relative w-full h-[50vh] rounded-lg overflow-hidden my-6">
          <Image
            src={normalizeImageUrl(listing.imageSrc)}
            alt={listing.title}
            fill
            style={{ objectFit: 'cover' }}
            sizes="100vw"
            priority
          />
          {listing.sourceUrl && (
            <div className="absolute top-3 left-3 bg-orange-600/90 text-white text-xs px-3 py-1 rounded shadow">
              Crawled • <a href={listing.sourceUrl} target="_blank" rel="noopener noreferrer" className="underline">Nguồn</a>
            </div>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <h2 className="text-xl font-semibold">Mô tả chi tiết</h2>
            <p className="text-gray-700 mt-2">{listing.description}</p>
            <hr className="my-4" />
            <h2 className="text-xl font-semibold mb-4">Vị trí</h2>
            <Map center={{ lat: listing.latitude, lng: listing.longitude }} />
            <hr className="my-6" />
            <div className="flex items-center gap-2">
              <span className="text-gray-700">Được đăng bởi:</span>
              <span className="font-semibold">{listing.user.name}</span>
            </div>
          </div>
          <div className="p-4 border rounded-lg shadow-lg h-full">
            <h3 className="text-2xl font-semibold text-center mb-4">
              {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(listing.price)}
              <span className="text-lg font-normal text-gray-600"> /đêm</span>
            </h3>
            <DateRange
              ranges={dateRange}
              onChange={onDateChange}
              minDate={new Date()}
              disabledDates={disabledDates}
              rangeColors={["#2563eb"]}
              locale={vi}
              showDateDisplay={false}
            />
            <hr className="my-4" />
            <div className="flex justify-between items-center text-xl font-semibold mb-4">
              <span>Tổng cộng:</span>
              <span>
                {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(totalPrice)}
              </span>
            </div>
            <Button 
              className="w-full" 
              size="lg"
              onClick={onCreateBooking}
              disabled={isLoading}
            >
              {isLoading ? "Đang xử lý..." : "Đặt ngay"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ListingClient
