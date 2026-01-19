/**
 * SpotSelectorTable Component
 * 
 * Multi-choice table for optional spot selection with:
 * - Checkboxes for multi-select
 * - Best visit time display (morning/afternoon/evening/night)
 * - Duration estimation
 * - Submit/Cancel/Skip/SelectAll/ClearAll actions
 */

import React, { useState, useMemo } from 'react';
import { Check, X, SkipForward, CheckSquare, Square, Clock, MapPin, Star, Sun, Sunset, Moon, Sunrise } from 'lucide-react';

// Time slot icons
const TimeSlotIcon = ({ slot }: { slot: string }) => {
  switch (slot) {
    case 'early_morning':
      return <Sunrise className="w-3 h-3 text-orange-400" />;
    case 'morning':
      return <Sun className="w-3 h-3 text-yellow-500" />;
    case 'afternoon':
      return <Sun className="w-3 h-3 text-amber-500" />;
    case 'evening':
      return <Sunset className="w-3 h-3 text-orange-500" />;
    case 'night':
      return <Moon className="w-3 h-3 text-indigo-500" />;
    default:
      return <Clock className="w-3 h-3 text-gray-400" />;
  }
};

// Time slot Vietnamese labels
const TIME_SLOT_LABELS: Record<string, string> = {
  early_morning: 'Sáng sớm',
  morning: 'Sáng',
  midday: 'Trưa',
  afternoon: 'Chiều',
  evening: 'Tối',
  night: 'Đêm',
};

type SpotRow = {
  id: string;
  name: string;
  category: string;
  rating: number;
  best_time: string[];
  avg_duration_min: number;
  area: string;
  image?: string;
  description?: string;
};

type SpotSelectorTableProps = {
  rows: SpotRow[];
  defaultSelectedIds: string[];
  destination: string;
  duration: number;
  onSubmit: (selectedIds: string[], removedIds: string[]) => void;
  onCancel: () => void;
  onSkip: () => void;
};

export const SpotSelectorTable: React.FC<SpotSelectorTableProps> = ({
  rows,
  defaultSelectedIds,
  destination,
  duration,
  onSubmit,
  onCancel,
  onSkip,
}) => {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    new Set(defaultSelectedIds)
  );

  const handleToggle = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    setSelectedIds(new Set(rows.map((r) => r.id)));
  };

  const handleClearAll = () => {
    setSelectedIds(new Set());
  };

  const handleSubmit = () => {
    const selected = Array.from(selectedIds);
    const removed = defaultSelectedIds.filter((id) => !selectedIds.has(id));
    onSubmit(selected, removed);
  };

  // Calculate stats
  const stats = useMemo(() => {
    const selected = rows.filter((r) => selectedIds.has(r.id));
    const totalDuration = selected.reduce((sum, r) => sum + r.avg_duration_min, 0);
    const avgPerDay = duration > 0 ? Math.round(selected.length / duration) : 0;
    return {
      count: selected.length,
      totalDuration,
      avgPerDay,
    };
  }, [rows, selectedIds, duration]);

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-500 to-indigo-500 text-white px-4 py-3">
        <h3 className="font-bold text-lg">🗓️ Chọn địa điểm cho {duration} ngày tại {destination}</h3>
        <p className="text-sm text-blue-100 mt-1">
          Đã chọn: <span className="font-bold">{stats.count}</span> địa điểm | 
          Trung bình: <span className="font-bold">{stats.avgPerDay}</span> địa điểm/ngày
        </p>
      </div>

      {/* Action Buttons - Top */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b">
        <div className="flex gap-2">
          <button
            onClick={handleSelectAll}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-100 rounded-lg hover:bg-blue-200 transition"
          >
            <CheckSquare className="w-3 h-3" />
            Chọn tất cả
          </button>
          <button
            onClick={handleClearAll}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition"
          >
            <Square className="w-3 h-3" />
            Bỏ chọn
          </button>
        </div>
        <div className="text-xs text-gray-500">
          <Clock className="w-3 h-3 inline mr-1" />
          Tổng: {Math.round(stats.totalDuration / 60)}h {stats.totalDuration % 60}m
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 sticky top-0 z-10">
            <tr className="text-left text-gray-600">
              <th className="px-3 py-2 w-10">
                <span className="sr-only">Chọn</span>
              </th>
              <th className="px-3 py-2">Địa điểm</th>
              <th className="px-3 py-2 hidden sm:table-cell">Loại</th>
              <th className="px-3 py-2 text-center">Rating</th>
              <th className="px-3 py-2">Thời điểm</th>
              <th className="px-3 py-2 text-right hidden md:table-cell">Thời lượng</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((row) => {
              const isSelected = selectedIds.has(row.id);
              return (
                <tr
                  key={row.id}
                  onClick={() => handleToggle(row.id)}
                  className={`cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-blue-50 hover:bg-blue-100'
                      : 'hover:bg-gray-50'
                  }`}
                >
                  <td className="px-3 py-2">
                    <div
                      className={`w-5 h-5 rounded border-2 flex items-center justify-center transition ${
                        isSelected
                          ? 'bg-blue-500 border-blue-500'
                          : 'border-gray-300'
                      }`}
                    >
                      {isSelected && <Check className="w-3 h-3 text-white" />}
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      {row.image && (
                        <img
                          src={row.image}
                          alt={row.name}
                          className="w-10 h-10 rounded object-cover"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                          }}
                        />
                      )}
                      <div>
                        <div className="font-medium text-gray-900 line-clamp-1">
                          {row.name}
                        </div>
                        <div className="text-xs text-gray-500 flex items-center gap-1">
                          <MapPin className="w-3 h-3" />
                          {row.area}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-2 hidden sm:table-cell">
                    <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded-full">
                      {row.category}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <Star className="w-3 h-3 text-yellow-500" />
                      <span className="font-medium">{row.rating}</span>
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-1 flex-wrap">
                      {row.best_time.slice(0, 2).map((time, idx) => (
                        <span
                          key={idx}
                          className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs bg-orange-50 text-orange-700 rounded"
                        >
                          <TimeSlotIcon slot={time} />
                          {TIME_SLOT_LABELS[time] || time}
                        </span>
                      ))}
                      {row.best_time.length > 2 && (
                        <span className="text-xs text-gray-400">
                          +{row.best_time.length - 2}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right hidden md:table-cell">
                    <span className="text-gray-600">
                      {row.avg_duration_min >= 60
                        ? `${Math.floor(row.avg_duration_min / 60)}h${row.avg_duration_min % 60 > 0 ? ` ${row.avg_duration_min % 60}m` : ''}`
                        : `${row.avg_duration_min}m`}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Footer Actions */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-t">
        <button
          onClick={onSkip}
          className="flex items-center gap-1 px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 transition"
        >
          <SkipForward className="w-4 h-4" />
          Bỏ qua
        </button>
        <div className="flex gap-2">
          <button
            onClick={onCancel}
            className="flex items-center gap-1 px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition"
          >
            <X className="w-4 h-4" />
            Hủy
          </button>
          <button
            onClick={handleSubmit}
            disabled={stats.count === 0}
            className={`flex items-center gap-1 px-4 py-2 text-sm font-medium text-white rounded-lg transition ${
              stats.count === 0
                ? 'bg-gray-300 cursor-not-allowed'
                : 'bg-blue-500 hover:bg-blue-600'
            }`}
          >
            <Check className="w-4 h-4" />
            Xác nhận ({stats.count})
          </button>
        </div>
      </div>
    </div>
  );
};

export default SpotSelectorTable;
