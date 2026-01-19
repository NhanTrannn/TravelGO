import { BrainCircuit, Search, Sparkles } from "lucide-react"
import React from "react"

// Danh sách các bước
const steps = [
  {
    icon: Search,
    title: "1. Nhập Yêu Cầu Tự Nhiên",
    description:
      "Thay vì điền vào nhiều ô, bạn chỉ cần gõ chính xác điều bạn muốn. Ví dụ: 'Tìm khách sạn lãng mạn ở Đà Lạt cho 2 người vào cuối tuần này'.",
  },
  {
    icon: BrainCircuit,
    title: "2. AI Phân Tích & Thấu Hiểu",
    description:
      "Hệ thống NLP (Xử lý Ngôn ngữ Tự nhiên) của chúng tôi sẽ phân tích câu của bạn để trích xuất địa điểm, ngày tháng, phong cách, giá cả và các thực thể khác.",
  },
  {
    icon: Sparkles,
    title: "3. Nhận Gợi Ý Cá Nhân Hóa",
    description:
      "Chúng tôi trả về các kết quả không chỉ khớp với từ khóa, mà còn khớp với *ý định* và *cảm xúc* trong yêu cầu của bạn, giúp bạn tìm được lựa chọn hoàn hảo.",
  },
]

// Đây là một Server Component vì nó không cần state hay tương tác
const HowItWorks = () => {
  return (
    <section className="bg-gray-50">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Tiêu đề khu vực */}
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900">
            Cách <span className="text-blue-600">TravelGO</span> Hoạt Động
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Trải nghiệm sức mạnh của AI trong việc lập kế hoạch du lịch.
          </p>
        </div>

        {/* Lưới 3 cột cho các bước */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {steps.map((step, index) => {
            const Icon = step.icon // Lấy component Icon từ đối tượng
            return (
              <div
                key={index}
                className="flex flex-col items-center text-center p-6 bg-white rounded-lg shadow-md"
              >
                {/* Icon */}
                <div className="flex items-center justify-center h-16 w-16 rounded-full bg-blue-100 text-blue-600 mb-4">
                  <Icon className="h-8 w-8" />
                </div>
                {/* Tiêu đề bước */}
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {step.title}
                </h3>
                {/* Mô tả bước */}
                <p className="text-gray-600">{step.description}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

export default HowItWorks
