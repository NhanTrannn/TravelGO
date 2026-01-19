/**
 * B2B Hotel Dashboard Page
 */
'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { useB2BAuth } from '@/hooks/useHotelDashboard';
import HotelDashboard from '@/components/features/HotelDashboard';

export default function B2BDashboardPage() {
  const router = useRouter();
  const { isAuthenticated, loading, logout } = useB2BAuth();

  React.useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/business/login');
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Đang kiểm tra xác thực...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Will redirect to login
  }

  return (
    <div>
      {/* Logout Button */}
      <div className="fixed top-4 right-4 z-50">
        <button
          onClick={logout}
          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition shadow-lg"
        >
          🚪 Đăng xuất
        </button>
      </div>

      {/* Dashboard Component */}
      <HotelDashboard />
    </div>
  );
}
