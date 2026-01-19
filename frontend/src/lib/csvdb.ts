// CSV Data Manager - Thay thế Prisma
import { parse } from 'csv-parse/sync';
import { stringify } from 'csv-stringify/sync';
import fs from 'fs';
import path from 'path';

const DATA_DIR = path.join(process.cwd(), 'data');

// Đảm bảo thư mục data tồn tại
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

// Interface cho dữ liệu
export interface Hotel {
  id: string;
  title: string;
  description: string;
  imageSrc: string;
  location: string;
  price: number;
  sourceUrl?: string;
  latitude: number;
  longitude: number;
  rating?: number;
  createdAt: string;
  updatedAt: string;
}

export interface User {
  id: string;
  name?: string;
  email?: string;
  password?: string;
  image?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Booking {
  id: string;
  userId: string;
  listingId: string;
  startDate: string;
  endDate: string;
  totalPrice: number;
  status: 'PENDING' | 'PAID' | 'CANCELLED';
  createdAt: string;
}

// Helper functions
function readCSV<T>(filename: string): T[] {
  const filePath = path.join(DATA_DIR, filename);

  if (!fs.existsSync(filePath)) {
    return [];
  }

  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    if (!content.trim()) return [];

    const records = parse(content, {
      columns: true,
      skip_empty_lines: true,
      cast: true,
      cast_date: false,
    }) as T[];

    return records;
  } catch (error) {
    console.error(`Error reading ${filename}:`, error);
    return [];
  }
}

function writeCSV<T>(filename: string, data: T[]): void {
  const filePath = path.join(DATA_DIR, filename);

  if (data.length === 0) {
    fs.writeFileSync(filePath, '', 'utf-8');
    return;
  }

  const csv = stringify(data, {
    header: true,
    quoted: true,
  });

  fs.writeFileSync(filePath, csv, 'utf-8');
}

function generateId(): string {
  return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Hotels/Listings Management
export const hotels = {
  findMany: (options?: {
    where?: Partial<Hotel>;
    orderBy?: { [key: string]: 'asc' | 'desc' };
    take?: number;
  }): Hotel[] => {
    let data = readCSV<Hotel>('hotels.csv');

    // Apply filters
    if (options?.where) {
      data = data.filter(hotel => {
        return Object.entries(options.where!).every(([key, value]) => {
          if (value === undefined) return true;
          return hotel[key as keyof Hotel] === value;
        });
      });
    }

    // Apply sorting
    if (options?.orderBy) {
      const [field, order] = Object.entries(options.orderBy)[0];
      data.sort((a, b) => {
        const aVal = a[field as keyof Hotel] ?? 0;
        const bVal = b[field as keyof Hotel] ?? 0;
        if (order === 'asc') {
          return aVal > bVal ? 1 : -1;
        }
        return aVal < bVal ? 1 : -1;
      });
    }

    // Apply limit
    if (options?.take) {
      data = data.slice(0, options.take);
    }

    return data;
  },

  findUnique: (where: { id: string }): Hotel | null => {
    const data = readCSV<Hotel>('hotels.csv');
    return data.find(h => h.id === where.id) || null;
  },

  create: (hotel: Omit<Hotel, 'id' | 'createdAt' | 'updatedAt'>): Hotel => {
    const data = readCSV<Hotel>('hotels.csv');
    const now = new Date().toISOString();

    const newHotel: Hotel = {
      ...hotel,
      id: generateId(),
      createdAt: now,
      updatedAt: now,
    };

    data.push(newHotel);
    writeCSV('hotels.csv', data);

    return newHotel;
  },

  update: (where: { id: string }, update: Partial<Hotel>): Hotel | null => {
    const data = readCSV<Hotel>('hotels.csv');
    const index = data.findIndex(h => h.id === where.id);

    if (index === -1) return null;

    data[index] = {
      ...data[index],
      ...update,
      updatedAt: new Date().toISOString(),
    };

    writeCSV('hotels.csv', data);
    return data[index];
  },

  delete: (where: { id: string }): Hotel | null => {
    const data = readCSV<Hotel>('hotels.csv');
    const index = data.findIndex(h => h.id === where.id);

    if (index === -1) return null;

    const deleted = data[index];
    data.splice(index, 1);
    writeCSV('hotels.csv', data);

    return deleted;
  },

  // Search by location
  searchByLocation: (location: string): Hotel[] => {
    const data = readCSV<Hotel>('hotels.csv');
    const searchTerm = location.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');

    return data.filter(hotel => {
      const hotelLocation = hotel.location.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
      return hotelLocation.includes(searchTerm);
    });
  },

  // Search by price range
  searchByPriceRange: (minPrice: number, maxPrice: number): Hotel[] => {
    const data = readCSV<Hotel>('hotels.csv');
    return data.filter(hotel => hotel.price >= minPrice && hotel.price <= maxPrice);
  },
};

// Users Management
export const users = {
  findUnique: (where: { id?: string; email?: string }): User | null => {
    const data = readCSV<User>('users.csv');

    if (where.id) {
      return data.find(u => u.id === where.id) || null;
    }

    if (where.email) {
      return data.find(u => u.email === where.email) || null;
    }

    return null;
  },

  create: (user: Omit<User, 'id' | 'createdAt' | 'updatedAt'>): User => {
    const data = readCSV<User>('users.csv');
    const now = new Date().toISOString();

    const newUser: User = {
      ...user,
      id: generateId(),
      createdAt: now,
      updatedAt: now,
    };

    data.push(newUser);
    writeCSV('users.csv', data);

    return newUser;
  },
};

// Bookings Management
export const bookings = {
  findMany: (where?: { userId?: string; listingId?: string }): Booking[] => {
    let data = readCSV<Booking>('bookings.csv');

    if (where) {
      data = data.filter(booking => {
        if (where.userId && booking.userId !== where.userId) return false;
        if (where.listingId && booking.listingId !== where.listingId) return false;
        return true;
      });
    }

    return data;
  },

  findUnique: (where: { id: string }): Booking | null => {
    const data = readCSV<Booking>('bookings.csv');
    return data.find(b => b.id === where.id) || null;
  },

  create: (booking: Omit<Booking, 'id' | 'createdAt'>): Booking => {
    const data = readCSV<Booking>('bookings.csv');

    const newBooking: Booking = {
      ...booking,
      id: generateId(),
      createdAt: new Date().toISOString(),
    };

    data.push(newBooking);
    writeCSV('bookings.csv', data);

    return newBooking;
  },

  update: (where: { id: string }, update: Partial<Booking>): Booking | null => {
    const data = readCSV<Booking>('bookings.csv');
    const index = data.findIndex(b => b.id === where.id);

    if (index === -1) return null;

    data[index] = {
      ...data[index],
      ...update,
    };

    writeCSV('bookings.csv', data);
    return data[index];
  },
};

// Export unified interface like Prisma
const csvDB = {
  listing: hotels,
  user: users,
  booking: bookings,
};

export default csvDB;
