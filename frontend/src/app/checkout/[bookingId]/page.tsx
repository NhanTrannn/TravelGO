"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import axios from "axios"
import Image from "next/image"
import { Button } from "@/components/ui/Button"
import toast from "react-hot-toast"

const MOMO_QR = "https://upload.wikimedia.org/wikipedia/commons/d/d0/QR_code_for_mobile_English_Wikipedia.svg"
const BANK_QR = "https://upload.wikimedia.org/wikipedia/commons/d/d0/QR_code_for_mobile_English_Wikipedia.svg"

type BookingDetail = {
  id: string
  startDate: string
  endDate: string
  totalPrice: number
  listing: { title: string; imageSrc: string }
}

export default function CheckoutPage({ params }: { params: { bookingId: string } }) {
  const router = useRouter()
  const [booking, setBooking] = useState<BookingDetail | null>(null)
  const [method, setMethod] = useState<"momo" | "bank">("momo")
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    axios.get(`/api/bookings/${params.bookingId}`).then((res) => setBooking(res.data))
  }, [params.bookingId])

  const handlePaymentSuccess = async () => {
    setIsLoading(true)
    try {
      await axios.patch(`/api/bookings/${params.bookingId}`, { status: "PAID" })
      toast.success("Thanh toán thành công!")
      router.push("/trips")
    } catch {
      toast.error("Lỗi xử lý thanh toán")
    } finally {
      setIsLoading(false)
    }
  }

  if (!booking) return <div className="p-10 text-center">Đang tải thông tin đơn hàng...</div>

  return (
    <div className="container mx-auto px-4 py-10 max-w-4xl">
      <h1 className="text-3xl font-bold mb-8 text-center">Thanh toán đơn hàng</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-gray-50 p-6 rounded-xl h-fit">
          <h2 className="text-xl font-semibold mb-4">Thông tin vé</h2>
          <div className="space-y-3 text-gray-700">
            <p><span className="font-medium">Khách sạn:</span> {booking.listing.title}</p>
            <p><span className="font-medium">Ngày đi:</span> {new Date(booking.startDate).toLocaleDateString('vi-VN')}</p>
            <p><span className="font-medium">Ngày về:</span> {new Date(booking.endDate).toLocaleDateString('vi-VN')}</p>
            <hr />
            <div className="flex justify-between text-xl font-bold text-blue-600 mt-2">
              <span>Tổng tiền:</span>
              <span>{new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(booking.totalPrice)}</span>
            </div>
          </div>
        </div>

        <div className="bg-white border p-6 rounded-xl shadow-sm">
          <h2 className="text-xl font-semibold mb-4">Chọn phương thức</h2>
          <div className="flex gap-4 mb-6">
            <button onClick={() => setMethod("momo")} className={`flex-1 py-3 border rounded-lg font-medium ${method === "momo" ? "border-pink-500 bg-pink-50 text-pink-600" : "border-gray-200"}`}>
              Ví Momo
            </button>
            <button onClick={() => setMethod("bank")} className={`flex-1 py-3 border rounded-lg font-medium ${method === "bank" ? "border-blue-500 bg-blue-50 text-blue-600" : "border-gray-200"}`}>
              Ngân hàng
            </button>
          </div>

          <div className="text-center">
            {method === "momo" ? (
              <div className="space-y-4">
                <p className="text-sm text-gray-500">Quét mã QR bằng ứng dụng Momo</p>
                <div className="relative w-48 h-48 mx-auto border-4 border-pink-500 rounded-lg overflow-hidden">
                  <Image src={MOMO_QR} alt="Momo QR" fill style={{ objectFit: 'cover' }} />
                </div>
                <p className="text-pink-600 font-bold">Nội dung CK: {params.bookingId}</p>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-gray-500">Chuyển khoản ngân hàng 24/7</p>
                <div className="relative w-48 h-48 mx-auto border-4 border-blue-500 rounded-lg overflow-hidden">
                  <Image src={BANK_QR} alt="Bank QR" fill style={{ objectFit: 'cover' }} />
                </div>
                <div className="bg-gray-100 p-3 rounded text-left text-sm">
                  <p>Bank: <strong>MB Bank</strong></p>
                  <p>STK: <strong>0987654321</strong></p>
                  <p>Tên: <strong>NGUYEN VAN A</strong></p>
                  <p className="mt-2 text-blue-600 font-bold">Nội dung: {params.bookingId}</p>
                </div>
              </div>
            )}
          </div>

          <div className="mt-8">
            <Button onClick={handlePaymentSuccess} disabled={isLoading} className="w-full bg-green-600 hover:bg-green-700 h-12 text-lg">
              {isLoading ? "Đang xác thực..." : "Tôi đã thanh toán"}
            </Button>
            <p className="text-xs text-center text-gray-400 mt-2">Hệ thống sẽ tự động xác nhận sau 1-2 phút</p>
          </div>
        </div>
      </div>
    </div>
  )
}
