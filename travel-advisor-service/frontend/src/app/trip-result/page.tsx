"use client";

import { useSearchParams } from 'next/navigation';
import { useEffect, useState, Suspense } from 'react';
import { MapPin, Clock, DollarSign, Users, Hotel, Calendar } from 'lucide-react';
/* eslint-disable @next/next/no-img-element */

interface Activity {
  time: string;
  activity: string;
  location?: string;
}

interface DayItinerary {
  day: number;
  title: string;
  activities: Activity[];
}

interface SelectedHotel {
  id: string;
  title: string;
  price: number;
  location: string;
  reason?: string;
  latitude?: number;
  longitude?: number;
  imageUrl?: string;
}

interface EstimatedCost {
  accommodation?: number;
  food?: number;
  transport?: number;
  activities?: number;
  total: number;
}

interface ItineraryData {
  selected_hotel: SelectedHotel | null;
  itinerary: DayItinerary[];
  estimated_cost: EstimatedCost;
}

interface TripResultData {
  status: string;
  message: string;
  data: {
    destination: string;
    duration: number;
    budget: string;
    travelers: string;
  };
  itinerary: ItineraryData;
}

function TripResultContent() {
  const searchParams = useSearchParams();
  const [tripData, setTripData] = useState<TripResultData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const dataParam = searchParams.get('data');
    if (!dataParam) {
      setError('Không tìm thấy dữ liệu lịch trình');
      return;
    }

    try {
      const parsed = JSON.parse(dataParam);
      // Use startTransition to avoid cascading render warning
      import('react').then(({ startTransition }) => {
        startTransition(() => {
          setTripData(parsed);
        });
      });
    } catch (err) {
      console.error('Parse error:', err);
      setError('Dữ liệu không hợp lệ');
    }
  }, [searchParams]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="text-xl text-red-600">{error}</p>
          <button 
            onClick={() => window.history.back()}
            className="mt-4 px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            Quay lại
          </button>
        </div>
      </div>
    );
  }

  if (!tripData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  const { data, itinerary } = tripData;
  const budgetLabels = { economical: 'Tiết kiệm', moderate: 'Trung bình', luxury: 'Sang trọng' };
  const travelersLabels = { solo: 'Một mình', couple: 'Cặp đôi', family: 'Gia đình', group: 'Nhóm bạn' };

  // Prepare map markers
  const markers = [];
  if (itinerary?.selected_hotel?.latitude && itinerary?.selected_hotel?.longitude) {
    markers.push({
      lat: itinerary.selected_hotel.latitude,
      lng: itinerary.selected_hotel.longitude,
      title: itinerary.selected_hotel.title,
      type: 'hotel'
    });
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white py-12">
        <div className="container mx-auto px-4">
          <h1 className="text-4xl font-bold mb-4">✈️ Lịch trình của bạn</h1>
          <div className="flex flex-wrap gap-6 text-lg">
            <div className="flex items-center gap-2">
              <MapPin className="w-5 h-5" />
              <span>{data.destination}</span>
            </div>
            <div className="flex items-center gap-2">
              <Calendar className="w-5 h-5" />
              <span>{data.duration} ngày</span>
            </div>
            <div className="flex items-center gap-2">
              <DollarSign className="w-5 h-5" />
              <span>{budgetLabels[data.budget as keyof typeof budgetLabels]}</span>
            </div>
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5" />
              <span>{travelersLabels[data.travelers as keyof typeof travelersLabels]}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Hotel & Cost */}
          <div className="space-y-6">
            {/* Selected Hotel */}
            {itinerary?.selected_hotel && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Hotel className="w-6 h-6 text-blue-600" />
                  <h2 className="text-xl font-bold">Khách sạn đề xuất</h2>
                </div>
                {itinerary.selected_hotel.imageUrl && (
                  <img 
                    src={itinerary.selected_hotel.imageUrl} 
                    alt={itinerary.selected_hotel.title}
                    className="w-full h-48 object-cover rounded-lg mb-4"
                  />
                )}
                <h3 className="font-bold text-lg mb-2">{itinerary.selected_hotel.title}</h3>
                <p className="text-gray-600 mb-2">{itinerary.selected_hotel.location}</p>
                <p className="text-2xl font-bold text-blue-600 mb-3">
                  {itinerary.selected_hotel.price.toLocaleString('vi-VN')} VNĐ/đêm
                </p>
                {itinerary.selected_hotel.reason && (
                  <p className="text-sm text-gray-700 bg-blue-50 p-3 rounded-lg">
                    💡 {itinerary.selected_hotel.reason}
                  </p>
                )}
              </div>
            )}

            {/* Estimated Cost */}
            {itinerary?.estimated_cost && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <div className="flex items-center gap-2 mb-4">
                  <DollarSign className="w-6 h-6 text-green-600" />
                  <h2 className="text-xl font-bold">Ước tính chi phí</h2>
                </div>
                <div className="space-y-3">
                  {itinerary.estimated_cost.accommodation && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Khách sạn</span>
                      <span className="font-semibold">{itinerary.estimated_cost.accommodation.toLocaleString('vi-VN')} ₫</span>
                    </div>
                  )}
                  {itinerary.estimated_cost.food && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Ăn uống</span>
                      <span className="font-semibold">{itinerary.estimated_cost.food.toLocaleString('vi-VN')} ₫</span>
                    </div>
                  )}
                  {itinerary.estimated_cost.transport && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Di chuyển</span>
                      <span className="font-semibold">{itinerary.estimated_cost.transport.toLocaleString('vi-VN')} ₫</span>
                    </div>
                  )}
                  {itinerary.estimated_cost.activities && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Vui chơi</span>
                      <span className="font-semibold">{itinerary.estimated_cost.activities.toLocaleString('vi-VN')} ₫</span>
                    </div>
                  )}
                  <div className="pt-3 border-t-2 border-gray-200 flex justify-between text-lg">
                    <span className="font-bold">Tổng cộng</span>
                    <span className="font-bold text-green-600">
                      {itinerary.estimated_cost.total.toLocaleString('vi-VN')} ₫
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Column - Itinerary Timeline */}
          <div className="lg:col-span-2 space-y-6">
            {/* Map - TODO: Integrate Google Maps later */}
            {markers.length > 0 && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                  <MapPin className="w-6 h-6 text-red-600" />
                  Vị trí khách sạn
                </h2>
                <div className="h-96 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center">
                  <div className="text-center text-gray-500">
                    <MapPin className="w-16 h-16 mx-auto mb-2" />
                    <p className="font-medium">{itinerary?.selected_hotel?.title}</p>
                    <p className="text-sm">{itinerary?.selected_hotel?.location}</p>
                    <p className="text-xs mt-2">🗺️ Bản đồ sẽ hiển thị ở đây</p>
                  </div>
                </div>
              </div>
            )}

            {/* Day-by-Day Itinerary */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                <Clock className="w-6 h-6 text-purple-600" />
                Lịch trình chi tiết
              </h2>
              <div className="space-y-6">
                {itinerary?.itinerary?.map((day) => (
                  <div key={day.day} className="border-l-4 border-blue-500 pl-4">
                    <h3 className="text-lg font-bold text-blue-600 mb-3">{day.title}</h3>
                    <div className="space-y-2">
                      {day.activities.map((activity, idx) => (
                        <div key={idx} className="flex gap-3 items-start">
                          <span className="text-sm font-semibold text-gray-500 min-w-[60px]">
                            {activity.time}
                          </span>
                          <div>
                            <p className="font-medium">{activity.activity}</p>
                            {activity.location && (
                              <p className="text-sm text-gray-600">📍 {activity.location}</p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-8 flex justify-center gap-4">
          <button
            onClick={() => window.history.back()}
            className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 font-medium"
          >
            ← Quay lại
          </button>
          <button
            onClick={() => window.print()}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            🖨️ In lịch trình
          </button>
        </div>
      </div>
    </div>
  );
}

export default function TripResultPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    }>
      <TripResultContent />
    </Suspense>
  );
}
