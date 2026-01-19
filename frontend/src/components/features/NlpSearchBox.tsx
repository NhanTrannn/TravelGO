"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import axios from "axios"
import qs from "query-string"
import { BrainCircuit, Search, MapPin, Hotel, Calendar } from "lucide-react"
import { Input } from "@/components/ui/Input"
import { Button } from "@/components/ui/Button"
import toast from "react-hot-toast"

const NlpSearchBox = () => {
  const [query, setQuery] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()

  const handleSearch = async () => {
    if (!query.trim()) return

    setIsLoading(true)
    // Hiệu ứng UX vui vẻ
    const loadingToast = toast.loading(
      query.length > 20 ? "AI đang phân tích ý định..." : "Đang tìm kiếm..."
    )

    try {
      // Gọi API phân tích ý định (Sử dụng model Python đã train/prompt)
      // Lưu ý: Chúng ta tái sử dụng route /api/chat nhưng với cờ analyze để lấy JSON
      const res = await axios.post("/api/chat/analyze", { message: query })
      const data = res.data // Expect: { intent, destination, budget, keywords, ... }

      toast.dismiss(loadingToast)
      
      const { intent, destination, budget, keywords } = data

      // --- LOGIC ĐIỀU HƯỚNG THÔNG MINH ---

      // CASE 1: Tìm Khách sạn -> Chuyển trang Listing
      if (intent === 'search_hotel' || intent === 'book_hotel') {
        const url = qs.stringifyUrl({
          url: '/search', // Trang danh sách khách sạn
          query: {
            location: destination,
            priceMax: budget, // Backend cần map "tiết kiệm" -> số tiền
            q: query
          }
        }, { skipNull: true })
        
        toast.success(`Tìm khách sạn tại ${destination || 'địa điểm mong muốn'}`)
        router.push(url)
      } 
      
      // CASE 2: Tìm Địa điểm chơi / Khám phá -> Chuyển trang Destinations
      else if (intent === 'suggest_spots' || intent === 'spot_detail') {
        const url = qs.stringifyUrl({
          url: '/destinations', // Trang danh sách tỉnh/địa điểm
          query: {
            mode: 'personalized',
            q: query, // Truyền câu query để trang kia gọi AI lọc tiếp
            province: destination
          }
        }, { skipNull: true })

        toast.success(`Khám phá địa điểm tại ${destination || 'Việt Nam'}`)
        router.push(url)
      }

      // CASE 3: Lên lịch trình / Chat chung -> Chuyển sang Chatbot
      else {
        // Chuyển sang trang Chat và mang theo câu hỏi đầu tiên
        const url = qs.stringifyUrl({
          url: '/chat',
          query: {
            initialMessage: query // Trang Chat sẽ tự động gửi câu này
          }
        }, { skipNull: true })

        toast.success("Chuyển sang Trợ lý AI để lên kế hoạch...")
        router.push(url)
      }

    } catch (error) {
      toast.dismiss(loadingToast)
      toast.error("Hệ thống đang bận, chuyển sang tìm kiếm thường...")
      console.error("NLP Analysis Error:", error)
      
      // Fallback: Chuyển sang trang search thường nếu AI lỗi
      router.push(`/search?q=${encodeURIComponent(query)}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSearch()
    }
  }

  return (
    <div className="relative w-full max-w-2xl mx-auto">
      <div className="relative flex items-center group">
        <Input 
          id="nlp-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="VD: tìm resort nha trang, chỗ chơi đà lạt, lên lịch đi sapa..."
          className="h-14 pl-12 pr-32 text-lg text-white placeholder:text-gray-200 bg-white/20 backdrop-blur-md shadow-xl rounded-full border-2 border-white/30 focus:border-white focus:bg-white/30 transition-all"
          disabled={isLoading}
        />
        
        {/* Icon thay đổi theo trạng thái input (Optional UX) */}
        <BrainCircuit className={`absolute left-4 h-6 w-6 transition-colors ${isLoading ? 'text-yellow-300 animate-pulse' : 'text-white'}`} />
        
        <Button 
          onClick={handleSearch}
          disabled={isLoading || !query.trim()}
          className="absolute right-2 bg-white text-blue-600 hover:bg-blue-50 rounded-full px-6 font-semibold shadow-lg transition-all hover:scale-105"
        >
          {isLoading ? <span className="animate-pulse">AI...</span> : "Tìm kiếm"}
        </Button>
      </div>
      
      {/* Gợi ý nhanh (Optional) */}
      {!query && (
        <div className="absolute top-16 left-0 w-full flex justify-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
            <span className="text-xs text-white/80 bg-black/20 px-2 py-1 rounded-md cursor-pointer hover:bg-black/40" onClick={() => setQuery("Resort Đà Nẵng gần biển")}>🏨 Resort Đà Nẵng</span>
            <span className="text-xs text-white/80 bg-black/20 px-2 py-1 rounded-md cursor-pointer hover:bg-black/40" onClick={() => setQuery("Chơi gì ở Hội An?")}>📍 Chơi gì Hội An</span>
            <span className="text-xs text-white/80 bg-black/20 px-2 py-1 rounded-md cursor-pointer hover:bg-black/40" onClick={() => setQuery("Lịch trình đi Sapa 3 ngày")}>📅 Lịch trình Sapa</span>
        </div>
      )}
    </div>
  )
}

export default NlpSearchBox