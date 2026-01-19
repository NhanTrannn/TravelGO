/**
 * UI Types - Định nghĩa cấu trúc dữ liệu cho giao diện
 * Component hiển thị chỉ cần biết CardItem, không cần biết nguồn gốc (Province/Spot)
 */

/**
 * Type chung cho Card hiển thị
 * Đây là interface trung gian giữa Backend Data và UI Component
 */
export type CardItem = {
  /** Unique identifier */
  id: string
  
  /** Loại item để xác định route khi click */
  type: 'PROVINCE' | 'SPOT'
  
  /** Tiêu đề chính */
  title: string
  
  /** Tiêu đề phụ (region cho province, address cho spot) */
  subtitle: string
  
  /** URL ảnh thumbnail */
  imageSrc: string
  
  /** Badge loại (hiển thị góc trên trái ảnh) */
  badge: string
  
  /** Thông tin chính (best_time cho province, cost cho spot) */
  infoPrimary: string
  
  /** Thông tin phụ (rating cho spot, null cho province) */
  infoSecondary?: string
  
  /** Link gốc từ nguồn data (optional) */
  sourceUrl?: string
  
  /** Slug để tạo URL (province-slug hoặc spot-slug) */
  slug: string
}

/**
 * Props cho FeaturedDestinations component
 */
export type FeaturedDestinationsProps = {
  items: CardItem[]
  title?: string
  subtitle?: string
}
