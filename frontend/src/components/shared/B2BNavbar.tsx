/**
 * B2B Dashboard Navbar
 * Navbar cho hotel managers với logout, refresh, hotel info
 */
'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { useB2BAuth } from '@/hooks/useHotelDashboard';

export default function B2BNavbar() {
  const router = useRouter();
  const { user, logout } = useB2BAuth();

  const handleLogout = () => {
    logout();
    router.push('/business/login');
  };

  const handleRefresh = () => {
    window.location.reload();
  };

  return (
    <nav className="bg-white shadow-md border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Left: Logo & Title */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center">
              <span className="text-2xl">🏨</span>
              <span className="ml-2 text-xl font-bold text-gray-900">
                B2B Dashboard
              </span>
            </div>
            {user && (
              <div className="hidden md:flex items-center space-x-2 text-sm text-gray-600">
                <span className="px-3 py-1 bg-blue-50 rounded-full">
                  Hotel ID: {user.hotel_id}
                </span>
              </div>
            )}
          </div>

          {/* Right: User Info & Actions */}
          <div className="flex items-center space-x-4">
            {user && (
              <>
                {/* User Info */}
                <div className="hidden md:flex items-center space-x-2 text-sm">
                  <div className="text-right">
                    <p className="font-semibold text-gray-900">{user.username}</p>
                    <p className="text-xs text-gray-500">{user.role}</p>
                  </div>
                  <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold">
                    {user.username?.charAt(0).toUpperCase()}
                  </div>
                </div>

                {/* Refresh Button */}
                <button
                  onClick={handleRefresh}
                  className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
                  title="Làm mới dữ liệu"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-5 w-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                </button>

                {/* Logout Button */}
                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-5 w-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                    />
                  </svg>
                  <span className="hidden sm:inline">Đăng xuất</span>
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Mobile User Info */}
      {user && (
        <div className="md:hidden px-4 pb-3 border-t border-gray-200">
          <div className="flex items-center justify-between mt-2">
            <div className="text-sm">
              <p className="font-semibold text-gray-900">{user.username}</p>
              <p className="text-xs text-gray-500">Hotel ID: {user.hotel_id}</p>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
