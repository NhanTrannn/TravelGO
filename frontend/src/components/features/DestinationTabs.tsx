"use client"

import { useState } from "react"
import Image from "next/image"

type TabType = "hotels" | "restaurants" | "attractions" | "tours" | "itineraries"

interface DestinationTabsProps {
  hotels: { id: string; name: string; priceRange: string | null; rating: number; imageSrc: string }[]
  restaurants: { id: string; name: string; priceRange: string | null; rating: number; imageSrc: string }[]
  attractions: { id: string; name: string; imageSrc: string }[]
  tours: { id: string; title: string; price: number; duration: string }[]
  itineraries: { id: string; title: string; totalDays: number; tags: string | null }[]
}

export default function DestinationTabs({ hotels, restaurants, attractions, tours, itineraries }: DestinationTabsProps) {
  const [activeTab, setActiveTab] = useState<TabType>("hotels")

  const tabs: { key: TabType; label: string }[] = [
    { key: "hotels", label: "Khách sạn" },
    { key: "restaurants", label: "Nhà hàng" },
    { key: "attractions", label: "Điểm vui chơi" },
    { key: "tours", label: "Tour" },
    { key: "itineraries", label: "Gợi ý Lịch trình" },
  ]

  return (
    <div>
      <div className="flex gap-2 border-b mb-6 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 font-medium border-b-2 transition whitespace-nowrap ${
              activeTab === tab.key ? "border-blue-600 text-blue-600" : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "hotels" && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {hotels.map((h) => (
            <a key={h.id} href={`/places/${h.id}`} className="border rounded-lg p-4 hover:shadow-lg transition flex gap-4">
              <div className="relative w-24 h-24 rounded overflow-hidden shrink-0">
                <Image src={h.imageSrc} alt={h.name} fill style={{ objectFit: 'cover' }} sizes="96px" />
              </div>
              <div className="flex-1">
                <h3 className="font-bold text-lg">{h.name}</h3>
                <p className="text-sm text-gray-600">{h.priceRange || 'Giá liên hệ'}</p>
                <p className="text-sm text-yellow-600">⭐ {h.rating}</p>
              </div>
            </a>
          ))}
        </div>
      )}

      {activeTab === "restaurants" && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {restaurants.map((r) => (
            <a key={r.id} href={`/places/${r.id}`} className="border rounded-lg p-4 hover:shadow-lg transition flex gap-4">
              <div className="relative w-24 h-24 rounded overflow-hidden shrink-0">
                <Image src={r.imageSrc} alt={r.name} fill style={{ objectFit: 'cover' }} sizes="96px" />
              </div>
              <div className="flex-1">
                <h3 className="font-bold text-lg">{r.name}</h3>
                <p className="text-sm text-gray-600">{r.priceRange || 'Giá liên hệ'}</p>
                <p className="text-sm text-yellow-600">⭐ {r.rating}</p>
              </div>
            </a>
          ))}
        </div>
      )}

      {activeTab === "attractions" && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {attractions.map((a) => (
            <a key={a.id} href={`/places/${a.id}`} className="border rounded-lg p-4 hover:shadow-lg transition flex gap-4">
              <div className="relative w-24 h-24 rounded overflow-hidden shrink-0">
                <Image src={a.imageSrc} alt={a.name} fill style={{ objectFit: 'cover' }} sizes="96px" />
              </div>
              <div className="flex-1">
                <h3 className="font-bold text-lg">{a.name}</h3>
              </div>
            </a>
          ))}
        </div>
      )}

      {activeTab === "tours" && (
        <div className="space-y-4">
          {tours.map((t) => (
            <div key={t.id} className="border rounded-lg p-4">
              <h3 className="font-bold text-lg">{t.title}</h3>
              <p className="text-gray-600">{t.duration}</p>
              <p className="text-blue-600 font-semibold">{new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(t.price)}</p>
            </div>
          ))}
        </div>
      )}

      {activeTab === "itineraries" && (
        <div className="space-y-4">
          {itineraries.map((it) => (
            <div key={it.id} className="border rounded-lg p-4">
              <h3 className="font-bold text-lg">{it.title}</h3>
              <p className="text-gray-600">{it.totalDays} ngày</p>
              {it.tags && <p className="text-sm text-gray-500">Tags: {it.tags}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
