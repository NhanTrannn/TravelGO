'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function BusinessPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to business dashboard
    router.replace('/business/dashboard');
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h2 className="text-xl font-semibold mb-2">Đang chuyển hướng...</h2>
        <p className="text-gray-600">Redirecting to Business Dashboard</p>
      </div>
    </div>
  );
}
