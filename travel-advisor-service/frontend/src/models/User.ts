import mongoose, { Schema, Document, Model } from 'mongoose';

export interface IUser extends Document {
  name?: string;
  email: string;
  emailVerified?: Date;
  password?: string;
  image?: string;
  hashedPassword?: string;
  createdAt: Date;
  updatedAt: Date;
}

const UserSchema = new Schema<IUser>({
  name: { type: String, trim: true },
  email: { type: String, unique: true, required: true, lowercase: true },
  emailVerified: { type: Date },
  password: { type: String },
  hashedPassword: { type: String },
  image: { type: String },
}, { 
  timestamps: true,
  collection: 'users'
});

// Note: `unique: true` on email already creates an index.
// Avoid defining a duplicate index to silence Mongoose warnings.

export default (mongoose.models.User as Model<IUser>) || 
  mongoose.model<IUser>('User', UserSchema);
