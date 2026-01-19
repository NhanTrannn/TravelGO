import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Hàm tiện ích để hợp nhất các class của Tailwind
 * Giúp giải quyết xung đột và quản lý class động.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}