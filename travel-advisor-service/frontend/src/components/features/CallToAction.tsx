"use client" // Bắt buộc vì dùng framer-motion

import { Button } from "@/components/ui/Button"
import { motion } from "framer-motion"
import { ArrowRight } from "lucide-react"

const CallToAction = () => {
  return (
    <section className="bg-slate-900">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="max-w-2xl mx-auto text-center">
          
          {/* Tiêu đề */}
          <motion.h2
            // 'whileInView' sẽ kích hoạt animation khi component lọt vào tầm nhìn
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} // Chỉ kích hoạt 1 lần
            transition={{ duration: 0.5 }}
            className="text-3xl font-bold text-white sm:text-4xl"
          >
            Sẵn sàng cho chuyến đi thông minh của bạn?
          </motion.h2>

          {/* Mô tả */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mt-4 text-lg text-slate-300"
          >
            Tạo tài khoản miễn phí để lưu địa điểm yêu thích, nhận gợi ý
            cá nhân hóa và lên kế hoạch cho hành trình tiếp theo.
          </motion.p>

          {/* Nút Kêu gọi Hành động */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-8"
          >
            {/* Chúng ta dùng component Button đã tạo */}
            <Button size="lg" className="bg-blue-600 hover:bg-blue-700">
              Bắt đầu miễn phí
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </motion.div>
        </div>
      </div>
    </section>
  )
}

export default CallToAction