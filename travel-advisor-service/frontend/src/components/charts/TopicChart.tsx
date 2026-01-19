/**
 * Topic Distribution Bar Chart
 * Hiển thị distribution của các topics
 */
'use client';

import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface TopicData {
  name: string;
  positive: number;
  negative: number;
  neutral: number;
}

interface TopicChartProps {
  data?: TopicData[];
}

export default function TopicChart({ data }: TopicChartProps) {
  // Mock data if not provided
  const chartData = data || [
    { name: 'Service', positive: 80, negative: 15, neutral: 20 },
    { name: 'Food', positive: 60, negative: 25, neutral: 18 },
    { name: 'Room', positive: 95, negative: 8, neutral: 12 },
    { name: 'Location', positive: 70, negative: 5, neutral: 25 },
    { name: 'Value', positive: 50, negative: 20, neutral: 15 },
  ];

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        📈 Topic Sentiment Analysis
      </h3>
      
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="positive" fill="#10b981" name="Positive" />
          <Bar dataKey="negative" fill="#ef4444" name="Negative" />
          <Bar dataKey="neutral" fill="#6b7280" name="Neutral" />
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4 text-sm text-gray-600">
        💡 <span className="font-medium">Insights:</span> Higher positive bars indicate strong performance in that area.
        Focus on topics with more negative reviews.
      </div>
    </div>
  );
}
