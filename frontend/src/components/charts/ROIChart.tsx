/**
 * ROI Projection Chart
 * Hiển thị dự báo ROI cho các recommendations
 */
'use client';

import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface ROIData {
  name: string;
  cost: number;
  revenue: number;
  roi: number;
}

interface ROIChartProps {
  recommendations?: string[]; // Action plans from pain points
}

export default function ROIChart({ recommendations }: ROIChartProps) {
  // Mock ROI data based on number of pain points
  const mockROIData: ROIData[] = [
    { name: 'Improve Service Quality', cost: 80, revenue: 200, roi: 150 },
    { name: 'Upgrade Facilities', cost: 120, revenue: 300, roi: 150 },
    { name: 'Staff Training Program', cost: 50, revenue: 150, roi: 200 },
    { name: 'Menu Enhancement', cost: 40, revenue: 120, roi: 200 },
  ];

  // Use number of recommendations to slice mock data
  const numRecs = recommendations?.length || 2;
  const data: ROIData[] = mockROIData.slice(0, Math.max(2, numRecs));

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        💰 ROI Projection by Recommendation
      </h3>
      
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" angle={-15} textAnchor="end" height={80} />
          <YAxis label={{ value: 'Million VND', angle: -90, position: 'insideLeft' }} />
          <Tooltip />
          <Legend />
          <Bar dataKey="cost" fill="#ef4444" name="Investment (M VND)" />
          <Bar dataKey="revenue" fill="#10b981" name="Expected Revenue (M VND)" />
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4 p-4 bg-blue-50 rounded-lg">
        <div className="font-semibold text-blue-900 mb-2">📊 ROI Summary:</div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          {data.map((item, idx) => (
            <div key={idx} className="flex justify-between">
              <span className="text-gray-700">{item.name}:</span>
              <span className="font-bold text-blue-600">{item.roi}% ROI</span>
            </div>
          ))}
        </div>
        <div className="mt-3 text-sm text-gray-600">
          💡 Higher ROI means better return on investment. Prioritize recommendations with ROI &gt; 150%.
        </div>
      </div>
    </div>
  );
}
