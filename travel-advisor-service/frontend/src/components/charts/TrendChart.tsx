/**
 * Sentiment Trend Line Chart
 * Hiển thị xu hướng sentiment theo thời gian
 */
'use client';

import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface TrendData {
  month: string;
  positive: number;
  negative: number;
  neutral: number;
}

interface TrendChartProps {
  data?: TrendData[];
}

export default function TrendChart({ data }: TrendChartProps) {
  // Mock data if not provided - last 6 months
  const chartData = data || [
    { month: 'Jul', positive: 70, negative: 15, neutral: 15 },
    { month: 'Aug', positive: 68, negative: 18, neutral: 14 },
    { month: 'Sep', positive: 72, negative: 14, neutral: 14 },
    { month: 'Oct', positive: 71, negative: 16, neutral: 13 },
    { month: 'Nov', positive: 73, negative: 13, neutral: 14 },
    { month: 'Dec', positive: 72, negative: 14, neutral: 14 },
  ];

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        📉 Sentiment Trend (Last 6 Months)
      </h3>
      
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="month" />
          <YAxis label={{ value: '% Reviews', angle: -90, position: 'insideLeft' }} />
          <Tooltip />
          <Legend />
          <Line 
            type="monotone" 
            dataKey="positive" 
            stroke="#10b981" 
            strokeWidth={2}
            name="Positive %"
          />
          <Line 
            type="monotone" 
            dataKey="negative" 
            stroke="#ef4444" 
            strokeWidth={2}
            name="Negative %"
          />
          <Line 
            type="monotone" 
            dataKey="neutral" 
            stroke="#6b7280" 
            strokeWidth={2}
            name="Neutral %"
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
        <div className="text-center">
          <div className="text-green-600 font-semibold">↗ Trending Up</div>
          <div className="text-gray-600">Positive reviews increasing</div>
        </div>
        <div className="text-center">
          <div className="text-red-600 font-semibold">↘ Declining</div>
          <div className="text-gray-600">Negative reviews stable</div>
        </div>
        <div className="text-center">
          <div className="text-blue-600 font-semibold">→ Stable</div>
          <div className="text-gray-600">Overall satisfaction good</div>
        </div>
      </div>
    </div>
  );
}
