/**
 * Destination Adapter - Chuyển đổi dữ liệu Database sang UI Format
 * Áp dụng Adapter Pattern để tách biệt Data Layer và UI Layer
 * UPDATED: Fix lỗi _id undefined, chuẩn hóa ID và xử lý ảnh an toàn
 */

import { CardItem } from '@/types/ui'

const DEFAULT_IMAGE = 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800'

/**
 * Helper: Normalize image URL
 * Xử lý các trường hợp link hỏng, thiếu protocol, hoặc link tương đối
 */
export const normalizeImageUrl = (url?: string | null): string => {
  // 1. Kiểm tra đầu vào: Nếu null/undefined/rỗng -> Trả về ảnh mặc định
  if (!url || typeof url !== 'string') return DEFAULT_IMAGE;

  // 2. Xóa khoảng trắng thừa (quan trọng vì data crawl hay bị dính cách/xuống dòng)
  const cleanUrl = url.trim();
  if (!cleanUrl) return DEFAULT_IMAGE;

  // 3. Nếu là link tuyệt đối (http/https) -> Giữ nguyên
  // Đây là dòng giúp ảnh từ media2.gody.vn hiển thị đúng
  if (cleanUrl.startsWith('http://') || cleanUrl.startsWith('https://')) {
    return cleanUrl;
  }

  // 4. Nếu là link thiếu giao thức (//media...) -> Thêm https:
  if (cleanUrl.startsWith('//')) {
    return `https:${cleanUrl}`;
  }

  // 5. Nếu là link tương đối (/uploads...) -> Thêm domain gốc Gody
  if (cleanUrl.startsWith('/')) {
    return `https://gody.vn${cleanUrl}`;
  }

  // 6. Trường hợp còn lại (link hỏng/không rõ định dạng) -> Fallback ảnh mặc định
  return DEFAULT_IMAGE;
}

/**
 * Chuyển đổi Province từ MongoDB sang CardItem
 */
export const mapProvinceToCard = (province: any): CardItem => {
  // Map region code sang label tiếng Việt
  const regionLabels: Record<string, string> = {
    north: 'Miền Bắc',
    central: 'Miền Trung', 
    south: 'Miền Nam',
    highlands: 'Tây Nguyên'
  }

  // [FIX] Logic lấy ID an toàn
  let safeId = 'unknown-province';
  if (province.id) safeId = province.id;
  else if (province.province_id) safeId = province.province_id;
  else if (province._id) safeId = province._id.toString();

  // Xử lý ảnh: Ưu tiên các trường ảnh có thể có
  const rawImage = province.image || province.img_url || province.imageSrc;
  const imageSrc = normalizeImageUrl(rawImage);

  return {
    id: safeId,
    type: 'PROVINCE',
    title: province.name || 'Tên đang cập nhật',
    subtitle: province.region_detail || regionLabels[province.region] || province.region || 'Việt Nam',
    imageSrc: imageSrc,
    badge: 'Tỉnh thành',
    infoPrimary: province.best_time ? `📅 ${province.best_time}` : '📅 Quanh năm',
    infoSecondary: undefined, 
    sourceUrl: province.url || '',
    slug: safeId 
  }
}

/**
 * Chuyển đổi Spot từ MongoDB sang CardItem
 */
export const mapSpotToCard = (spot: any): CardItem => {
  // [FIX] Logic lấy ID an toàn
  let safeId = 'unknown-spot';
  if (spot.id) safeId = spot.id;
  else if (spot._id) safeId = spot._id.toString();

  // Format rating hiển thị
  const ratingDisplay = spot.rating 
    ? `⭐ ${Number(spot.rating).toFixed(1)} (${spot.reviews_count || 0})`
    : undefined

  // Format cost hiển thị
  const costDisplay = spot.cost 
    ? (String(spot.cost).toLowerCase() === 'miễn phí' ? '🆓 Miễn phí' : `💰 ${spot.cost}`)
    : '💰 Chưa rõ'

  const rawImage = spot.image || spot.img_url;
  const imageSrc = normalizeImageUrl(rawImage);

  return {
    id: safeId,
    type: 'SPOT',
    title: spot.name || 'Địa điểm chưa đặt tên',
    subtitle: spot.address || 'Đang cập nhật địa chỉ',
    imageSrc: imageSrc,
    badge: 'Địa điểm',
    infoPrimary: costDisplay,
    infoSecondary: ratingDisplay,
    sourceUrl: spot.url || '',
    slug: safeId
  }
}

/**
 * Helper: Chuyển đổi một mảng mixed provinces/spots sang CardItem[]
 */
export const mapMixedToCards = (items: any[]): CardItem[] => {
  if (!Array.isArray(items)) return [];
  
  return items.map(item => {
    // Logic phát hiện type
    if (item.type === 'province' || ('region' in item && !item.address)) {
      return mapProvinceToCard(item)
    } else if (item.type === 'spot' || ('province_id' in item && 'address' in item)) {
      return mapSpotToCard(item)
    } else {
      return mapProvinceToCard(item)
    }
  })
}