/**
 * B2B Hotel Dashboard Component
 * Hiển thị pain points và insights cho hotel business
 */
'use client';

import React from 'react';
import { useHotelDashboard, usePainPoints } from '@/hooks/useHotelDashboard';
import SentimentChart from '@/components/charts/SentimentChart';
import TopicChart from '@/components/charts/TopicChart';
import TrendChart from '@/components/charts/TrendChart';
import ROIChart from '@/components/charts/ROIChart';

// Severity badge colors
const severityColors = {
  High: 'bg-red-100 text-red-800 border-red-300',
  Medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  Low: 'bg-blue-100 text-blue-800 border-blue-300',
};

// Sentiment badge colors
const sentimentColors = {
  Positive: 'bg-green-100 text-green-800',
  Negative: 'bg-red-100 text-red-800',
  Neutral: 'bg-gray-100 text-gray-800',
};

export default function HotelDashboard() {
  const { data, loading, error } = useHotelDashboard();
  const { painPoints } = usePainPoints();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Đang tải dữ liệu khách sạn...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center text-red-600">
          <p className="text-xl font-bold">⚠️ Lỗi tải dữ liệu</p>
          <p className="mt-2">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Thử lại
          </button>
        </div>
      </div>
    );
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const hotel_info = (data?.hotel_info || {}) as any;
  const kpi_stats = data?.kpi_stats || { total: 0, positive: 0, negative: 0, neutral: 0, avg_sentiment_score: 0 };
  const recent_reviews = data?.recent_reviews || [];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {hotel_info?.name || 'Dashboard'}
          </h1>
          <p className="text-gray-600 mt-1">{hotel_info?.address}</p>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-sm text-gray-600">Tổng đánh giá (30 ngày)</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{kpi_stats.total}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-sm text-gray-600">Tích cực</p>
          <p className="text-3xl font-bold text-green-600 mt-2">
            {kpi_stats.positive}
            <span className="text-sm ml-2">
              ({kpi_stats.total > 0 ? ((kpi_stats.positive / kpi_stats.total) * 100).toFixed(1) : 0}%)
            </span>
          </p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-sm text-gray-600">Tiêu cực</p>
          <p className="text-3xl font-bold text-red-600 mt-2">
            {kpi_stats.negative}
            <span className="text-sm ml-2">
              ({kpi_stats.total > 0 ? ((kpi_stats.negative / kpi_stats.total) * 100).toFixed(1) : 0}%)
            </span>
          </p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-sm text-gray-600">Điểm TB</p>
          <p className="text-3xl font-bold text-blue-600 mt-2">
            {kpi_stats.avg_sentiment_score.toFixed(2)}
            <span className="text-sm">/1.0</span>
          </p>
        </div>
      </div>

      {/* Data Visualizations */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          📊 Trực quan hóa dữ liệu
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Sentiment Distribution */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Phân bố cảm xúc</h3>
            <SentimentChart
              positive={kpi_stats.positive}
              negative={kpi_stats.negative}
              neutral={kpi_stats.neutral}
            />
          </div>

          {/* Topic Analysis */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Phân tích theo chủ đề</h3>
            <TopicChart />
          </div>

          {/* Sentiment Trends */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Xu hướng 6 tháng</h3>
            <TrendChart />
          </div>

          {/* ROI Projections */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Dự báo ROI</h3>
            <ROIChart recommendations={painPoints.map(p => p.action_plan)} />
          </div>
        </div>
      </div>

      {/* Pain Points Section */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          🔴 Nỗi đau khách hàng (Pain Points)
        </h2>
        
        {painPoints.length === 0 ? (
          <div className="bg-white p-8 rounded-lg shadow text-center text-gray-500">
            <p>Chưa có dữ liệu pain points. Vui lòng chạy pipeline phân tích.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {painPoints.map((point, index) => (
              <div
                key={index}
                className="bg-white border-l-4 border-red-500 p-6 rounded-lg shadow hover:shadow-lg transition"
              >
                {/* Header */}
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-bold text-gray-900">
                    {point.cluster_name}
                  </h3>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                      severityColors[point.severity]
                    }`}
                  >
                    {point.severity}
                  </span>
                </div>

                {/* Volume */}
                <p className="text-sm text-gray-600 mb-3">
                  📊 Số lượng phản ánh: <span className="font-semibold">{point.volume}</span>
                </p>

                {/* Representative Quotes */}
                {point.representative_quotes && point.representative_quotes.length > 0 && (
                  <div className="mb-4">
                    <p className="text-sm font-semibold text-gray-700 mb-2">
                      💬 Trích dẫn tiêu biểu:
                    </p>
                    <div className="space-y-2">
                      {point.representative_quotes.slice(0, 2).map((quote, idx) => (
                        <p key={idx} className="text-sm italic text-gray-600 pl-3 border-l-2 border-gray-300">
                          &ldquo;{quote}&rdquo;
                        </p>
                      ))}
                    </div>
                  </div>
                )}

                {/* Action Plan */}
                <div className="bg-blue-50 p-3 rounded-lg">
                  <p className="text-xs font-semibold text-blue-900 mb-1">
                    💡 Đề xuất hành động:
                  </p>
                  <p className="text-sm text-blue-800">{point.action_plan}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Reviews Section */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          📝 Đánh giá gần đây
        </h2>
        
        {recent_reviews.length === 0 ? (
          <div className="bg-white p-8 rounded-lg shadow text-center text-gray-500">
            <p>Chưa có đánh giá nào.</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Nguồn
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Nội dung
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Cảm xúc
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Ngày
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {recent_reviews && recent_reviews.length > 0 ? (
                    recent_reviews.slice(0, 10).map((review) => (
                      <tr key={review._id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {review.source}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-700 max-w-md truncate">
                        {review.original_text}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-semibold ${
                            sentimentColors[review.ai_analysis.sentiment]
                          }`}
                        >
                          {review.ai_analysis.sentiment}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {review.review_date ? new Date(review.review_date).toISOString().split('T')[0] : 'N/A'}
                      </td>
                    </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="px-6 py-4 text-center text-gray-500">
                        Chưa có dữ liệu review
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
