import mongoose, { Schema, Document, Model } from 'mongoose';

export interface IBooking extends Document {
  userId: string;
  listingId: string;
  startDate: Date;
  endDate: Date;
  totalPrice: number;
  status: 'PENDING' | 'CONFIRMED' | 'CANCELLED';
  createdAt: Date;
  updatedAt: Date;
}

const BookingSchema = new Schema<IBooking>({
  userId: { type: String, required: true, index: true },
  listingId: { type: String, required: true, index: true },
  startDate: { type: Date, required: true },
  endDate: { type: Date, required: true },
  totalPrice: { type: Number, required: true },
  status: { 
    type: String, 
    enum: ['PENDING', 'CONFIRMED', 'CANCELLED'], 
    default: 'PENDING' 
  },
}, { 
  timestamps: true,
  collection: 'bookings'
});

// Compound index for efficient date range queries
BookingSchema.index({ listingId: 1, startDate: 1, endDate: 1 });
BookingSchema.index({ userId: 1, status: 1 });

export default (mongoose.models.Booking as Model<IBooking>) || 
  mongoose.model<IBooking>('Booking', BookingSchema);
