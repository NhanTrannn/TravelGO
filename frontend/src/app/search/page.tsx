/* eslint-disable @typescript-eslint/no-explicit-any */
import dbConnect from '@/lib/db'
import Listing from '@/models/Listing'
import FeaturedDestinations from '@/components/features/FeaturedDestinations'
import { MapPin, DollarSign, Tag } from 'lucide-react'
import Link from 'next/link'

// --- HELPER FUNCTIONS (Giữ nguyên logic xử lý tiếng Việt của bạn) ---
function foldAccents(input: string): string {
  return input
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/đ/gi, 'd')
    .toLowerCase();
}

function tokenizeQuery(q: string): string[] {
  return Array.from(new Set(
    foldAccents(q)
      .split(/[^a-z0-9]+/)
      .filter(t => t.length >= 2)
  )).slice(0, 12);
}

type SearchParams = {
  location?: string
  priceMax?: string
  keywords?: string
  q?: string
}

// [FIX] Props type cho Next.js 15 (searchParams là Promise)
type PageProps = {
  searchParams: Promise<SearchParams>
}

export default async function SearchPage({ searchParams }: PageProps) {
  await dbConnect();
  
  // [FIX] Await searchParams trước khi destructure
  const { location, priceMax, keywords, q } = await searchParams;

  // --- BUILD MONGO QUERY (Logic cũ của bạn, rất tốt) ---
  const query: any = {};
  
  if (location) {
    const folded = foldAccents(location);
    query.$or = [
      { location: { $regex: location, $options: 'i' } },
      { normalizedLocation: { $regex: folded.replace(/\s+/g,'[\s,/-]*'), $options: 'i' } }
    ];
  }
  
  if (priceMax) {
    query.price = { $lte: parseInt(priceMax) };
  }
  
  if (keywords) {
    const folded = foldAccents(keywords);
    const kwRegex = { $regex: keywords, $options: 'i' };
    const foldedRegex = { $regex: folded.replace(/\s+/g,'[\s,/-]*'), $options: 'i' };
    const kwTokens = tokenizeQuery(keywords);
    const tokenQuery = kwTokens.length ? { searchTokens: { $in: kwTokens } } : {};

    if (query.$or) {
      query.$or.push(
        { title: kwRegex },
        { description: kwRegex },
        { normalizedTitle: foldedRegex },
        tokenQuery
      );
    } else {
      query.$or = [
        { title: kwRegex },
        { description: kwRegex },
        { normalizedTitle: foldedRegex },
        tokenQuery
      ];
    }
  }

  // Full-text fallback
  if (!location && !keywords && q) {
    const tokens = tokenizeQuery(q);
    const folded = foldAccents(q);
    const regexFolded = { $regex: folded.replace(/\s+/g,'[\s,/-]*'), $options: 'i' };
    query.$or = [
      { title: regexFolded },
      { description: regexFolded },
      { normalizedTitle: regexFolded },
      { normalizedLocation: regexFolded },
      { searchTokens: { $in: tokens } }
    ];
  }

  // Execute Query
  const rawListings = await Listing.find(query)
    .sort({ createdAt: -1 })
    .limit(50) // Limit lại để tránh load quá nhiều
    .lean();

  // Format Listings
  const PLACEHOLDER_IMG = 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800'
  const listings = rawListings.map((listing: any) => ({
    ...listing,
    _id: listing._id.toString(),
    id: listing._id.toString(),
    createdAt: listing.createdAt?.toISOString(),
    updatedAt: listing.updatedAt?.toISOString(),
    // Fix logic ảnh: ưu tiên imageSrc, fallback placeholder
    imageSrc: (listing.imageSrc && listing.imageSrc.trim() !== '') ? listing.imageSrc : PLACEHOLDER_IMG,
  }));

  return (
    <div className="min-h-screen bg-linear-to-b from-blue-50 to-white py-12 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-4">
            Kết quả tìm kiếm 🔍
          </h1>
          
          {/* Show Original Query if NLP extracted params */}
          {(q && (location || priceMax)) && (
            <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-100">
              <p className="text-sm text-gray-600 mb-1">Từ khóa gốc:</p>
              <p className="text-lg font-medium text-gray-800">&ldquo;{q}&rdquo;</p>
            </div>
          )}

          {/* Active Filters Badges */}
          <div className="flex flex-wrap gap-3">
            {location && (
              <div className="flex items-center gap-2 px-4 py-2 bg-green-100 text-green-800 rounded-full border border-green-200">
                <MapPin className="h-4 w-4" />
                <span className="font-medium">{location}</span>
              </div>
            )}
            
            {priceMax && (
              <div className="flex items-center gap-2 px-4 py-2 bg-yellow-100 text-yellow-800 rounded-full border border-yellow-200">
                <DollarSign className="h-4 w-4" />
                <span className="font-medium">
                  Max: {parseInt(priceMax).toLocaleString('vi-VN')} VNĐ
                </span>
              </div>
            )}
            
            {keywords && (
              <div className="flex items-center gap-2 px-4 py-2 bg-purple-100 text-purple-800 rounded-full border border-purple-200">
                <Tag className="h-4 w-4" />
                <span className="font-medium">{keywords}</span>
              </div>
            )}
          </div>
        </div>

        {/* Results Count */}
        <div className="mb-6 flex justify-between items-center">
          <p className="text-lg text-gray-700">
            Tìm thấy <span className="font-bold text-blue-600">{listings.length}</span> kết quả
          </p>
        </div>

        {/* Render Listings */}
        {listings.length > 0 ? (
          <FeaturedDestinations listings={listings} />
        ) : (
          <div className="bg-white rounded-2xl shadow-lg p-12 text-center border border-gray-100">
            <div className="text-6xl mb-4">😢</div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">
              Không tìm thấy kết quả phù hợp
            </h2>
            <p className="text-gray-600 mb-6">
              Thử điều chỉnh yêu cầu tìm kiếm hoặc mở rộng phạm vi giá
            </p>
            <Link 
              href="/"
              className="inline-block px-6 py-3 bg-blue-600 text-white rounded-full font-medium hover:bg-blue-700 transition shadow-md hover:shadow-lg"
            >
              Về trang chủ
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}