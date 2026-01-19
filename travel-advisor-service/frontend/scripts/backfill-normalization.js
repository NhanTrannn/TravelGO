/* eslint-disable */
/**
 * Backfill normalized fields for existing listings.
 * Run: node scripts/backfill-normalization.js
 */
const mongoose = require('mongoose');
require('dotenv').config();

// Minimal schema (no TS import) pointing to existing collection
const listingSchema = new mongoose.Schema({
  title: String,
  location: String,
  normalizedTitle: String,
  normalizedLocation: String,
  searchTokens: [String]
}, { collection: 'listings' });
const Listing = mongoose.models.Listing || mongoose.model('Listing', listingSchema);

function foldAccents(input) {
  if (!input) return '';
  return input
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/đ/gi, 'd')
    .toLowerCase();
}

async function run() {
  const uri = process.env.MONGODB_URI;
  if (!uri) {
    console.error('Missing MONGODB_URI');
    process.exit(1);
  }
  await mongoose.connect(uri);
  console.log('Connected MongoDB');
  const cursor = Listing.find({}).cursor();
  let processed = 0;
  for await (const doc of cursor) {
    const needs = !doc.normalizedLocation || !doc.normalizedTitle || !doc.searchTokens;
    if (needs) {
      doc.normalizedTitle = foldAccents(doc.title);
      doc.normalizedLocation = foldAccents(doc.location);
      const raw = `${doc.title} ${doc.location}`.toLowerCase();
      const tokens = Array.from(new Set(
        raw
          .normalize('NFD')
          .replace(/\p{Diacritic}/gu, '')
          .replace(/đ/gi, 'd')
          .split(/[^a-z0-9]+/)
          .filter(t => t.length >= 2)
      ));
      doc.searchTokens = tokens.slice(0, 50);
      await doc.save();
      processed++;
    }
  }
  console.log(`Backfill complete. Updated ${processed} documents.`);
  await mongoose.disconnect();
}

run().catch(e => { console.error(e); process.exit(1); });
