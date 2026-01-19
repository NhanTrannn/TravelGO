import mongoose, { Schema, Document, Model } from 'mongoose';

export interface IStagingListing extends Document {
  sourceUrl: string;
  category: string;
  status: 'PENDING' | 'PROCESSED' | 'FAILED';
  rawJson: Record<string, any>;
  errorMessage?: string;
  processedAt?: Date;
  createdAt: Date;
  updatedAt: Date;
}

const StagingListingSchema = new Schema<IStagingListing>({
  sourceUrl: { type: String, required: true, unique: true, index: true },
  category: { type: String, required: true, default: 'UNKNOWN' },
  status: { 
    type: String, 
    enum: ['PENDING', 'PROCESSED', 'FAILED'], 
    default: 'PENDING',
    index: true
  },
  rawJson: { type: Schema.Types.Mixed, required: true },
  errorMessage: { type: String },
  processedAt: { type: Date },
}, { 
  timestamps: true,
  collection: 'staginglistings'
});

// Index for efficient processing queue queries
StagingListingSchema.index({ status: 1, createdAt: 1 });
StagingListingSchema.index({ category: 1, status: 1 });

export default (mongoose.models.StagingListing as Model<IStagingListing>) || 
  mongoose.model<IStagingListing>('StagingListing', StagingListingSchema);
