/**
 * Sentiment Distribution Chart Component
 * Pie chart hiển thị phân bố sentiment
 */
'use client';

import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface SentimentChartProps {
  positive: number;
  negative: number;
  neutral: number;
}

const COLORS = {
  Positive: '#10b981', // green-500
  Negative: '#ef4444', // red-500
  Neutral: '#6b7280',  // gray-500
};

export default function SentimentChart({ positive, negative, neutral }: SentimentChartProps) {
  const data = [
    { name: 'Positive', value: positive, color: COLORS.Positive },
    { name: 'Negative', value: negative, color: COLORS.Negative },
    { name: 'Neutral', value: neutral, color: COLORS.Neutral },
  ];

  const total = positive + negative + neutral;

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        📊 Sentiment Distribution
      </h3>
      
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, value }: any) => `${name}: ${value} (${((value/total)*100).toFixed(1)}%)`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-3 gap-4 text-center">
        <div className="p-3 bg-green-50 rounded">
          <div className="text-2xl font-bold text-green-600">{positive}</div>
          <div className="text-sm text-gray-600">Positive</div>
        </div>
        <div className="p-3 bg-red-50 rounded">
          <div className="text-2xl font-bold text-red-600">{negative}</div>
          <div className="text-sm text-gray-600">Negative</div>
        </div>
        <div className="p-3 bg-gray-50 rounded">
          <div className="text-2xl font-bold text-gray-600">{neutral}</div>
          <div className="text-sm text-gray-600">Neutral</div>
        </div>
      </div>
    </div>
  );
}
