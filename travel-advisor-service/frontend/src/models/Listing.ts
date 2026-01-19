import mongoose, { Schema, Document, Model } from 'mongoose';

// Utility to fold Vietnamese diacritics (basic accent removal + đ → d)
function foldAccents(input: string): string {
  if (!input) return '';
  return input
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/đ/gi, 'd')
    .toLowerCase();
}

export interface IListing extends Document {
  title: string;
  description: string;
  imageSrc: string;
  location: string;
  price: number;
  latitude: number;
  longitude: number;
  rating?: number;
  sourceUrl?: string;
  userId: string;
  createdAt: Date;
  updatedAt: Date;
  normalizedTitle?: string;
  normalizedLocation?: string;
  searchTokens?: string[];
}

const ListingSchema = new Schema<IListing>({
  title: { type: String, required: true, trim: true },
  description: { type: String, required: true },
  imageSrc: { type: String, default: 'https://placehold.co/600x400?text=No+Image' },
  location: { type: String, required: true, index: true },
  price: { type: Number, required: true, index: true },
  latitude: { type: Number, default: 10.762622 },
  longitude: { type: Number, default: 106.660172 },
  rating: { type: Number, default: 0, min: 0, max: 5 },
  sourceUrl: { type: String, unique: true, sparse: true },
  userId: { type: String, required: true, default: 'system' },
  normalizedTitle: { type: String, index: true },
  normalizedLocation: { type: String, index: true },
  // Avoid duplicate index definition: we define explicit index below
  searchTokens: { type: [String] },
}, { 
  timestamps: true,
  collection: 'listings'
});

// Indexes for better search performance
ListingSchema.index({ location: 'text', title: 'text', description: 'text' });
ListingSchema.index({ price: 1, location: 1 });
ListingSchema.index({ normalizedLocation: 1, normalizedTitle: 1 });
// Explicit single-field index for token search
ListingSchema.index({ searchTokens: 1 });

// Pre-save hook to populate normalized & token fields
// Use function signature with next callback (no args → success, with Error → fail)
ListingSchema.pre<IListing>('save', function(this: IListing) {
  try {
    if (!this.normalizedTitle || this.isModified('title')) {
      this.normalizedTitle = foldAccents(this.title);
    }
    if (!this.normalizedLocation || this.isModified('location')) {
      this.normalizedLocation = foldAccents(this.location);
    }
    const raw = `${this.title} ${this.location}`.toLowerCase();
    const tokens = Array.from(new Set(
      raw
        .normalize('NFD')
        .replace(/\p{Diacritic}/gu, '')
        .replace(/đ/gi, 'd')
        .split(/[^a-z0-9]+/)
        .filter(t => t.length >= 2)
    ));
    this.searchTokens = tokens.slice(0, 50);
  } catch (err) {
    console.error('Error in Listing pre-save normalization:', err);
  }
});

// Prevent OverwriteModelError during hot reload in development
export default (mongoose.models.Listing as Model<IListing>) || 
  mongoose.model<IListing>('Listing', ListingSchema);
