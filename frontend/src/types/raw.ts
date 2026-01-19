/**
 * Raw Data Types - Định nghĩa cấu trúc dữ liệu từ MongoDB
 */

/**
 * Dữ liệu Tỉnh thành từ collection: provinces_info
 */
export type ProvinceRaw = {
  _id: string
  slug: string
  name: string
  name_en: string
  region: string // "north" | "central" | "south" | "highlands"
  region_detail?: string // "Đông Bắc Bộ", "Tây Bắc Bộ", etc.
  description: string
  best_time: string // "Tháng 10 - 3"
  best_time_detail?: string
  image: string
  url: string
  highlights?: string[]
  cuisine?: string[]
  experience?: string[]
  updatedAt?: string
}

/**
 * Dữ liệu Địa điểm từ collection: spots_detailed
 */
export type SpotRaw = {
  _id: string
  id: string // spot slug
  name: string
  province_id: string
  address: string
  image: string
  rating: number
  reviews_count: number
  cost: string // "miễn phí" | "50.000 VNĐ" | etc.
  description_short?: string
  description_full?: string
  url: string
  tags?: string[]
  latitude?: number
  longitude?: number
  updatedAt?: string
}

/**
 * Helper type để serialize ObjectId sang string
 */
export type SerializedDocument<T> = Omit<T, '_id'> & { _id: string }
