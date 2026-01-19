"use client";

import React from "react";
import { Button } from "@/components/ui/Button";

export default function HeroSection() {
  return (
  <section className="relative bg-linear-to-r from-blue-500 to-purple-600 text-white py-20 px-4">
      <div className="container mx-auto text-center">
        <h1 className="text-4xl md:text-6xl font-bold mb-6">
          Khám phá du lịch với TravelGO
        </h1>
        <p className="text-xl md:text-2xl mb-8 max-w-3xl mx-auto">
          Tìm kiếm điểm đến lý tưởng của bạn bằng ngôn ngữ tự nhiên.
          Công nghệ AI giúp bạn khám phá những trải nghiệm du lịch tuyệt vời nhất.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Button size="lg" variant="default" className="bg-white text-blue-600 hover:bg-gray-100">
            Bắt đầu khám phá
          </Button>
          <Button size="lg" variant="outline" className="border-white text-white hover:bg-white/10">
            Tìm hiểu thêm
          </Button>
        </div>
      </div>

      {/* Decorative elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute top-10 left-10 w-20 h-20 bg-white/10 rounded-full blur-xl"></div>
        <div className="absolute bottom-10 right-10 w-32 h-32 bg-white/10 rounded-full blur-xl"></div>
      </div>
    </section>
  );
}
