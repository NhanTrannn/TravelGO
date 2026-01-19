import { notFound } from "next/navigation"
import ListingClient from "./ListingClient"
import dbConnect from "@/lib/db"
import Listing from "@/models/Listing"

export default async function ListingPage({ params }: { params: { id: string } }) {
  await dbConnect();

  const id = params.id;
  if (!id) return notFound();

  const doc = await Listing.findById(id).lean();
  if (!doc) return notFound();

  const serializedListing = {
    id: doc._id.toString(),
    title: doc.title,
    description: doc.description || '',
    imageSrc: doc.imageSrc || '',
    location: doc.location,
    price: Number(doc.price || 0),
    createdAt: (doc.createdAt as Date).toISOString(),
    latitude: Number((doc as any).latitude || 10.762622),
    longitude: Number((doc as any).longitude || 106.660172),
    sourceUrl: (doc as any).sourceUrl || null,
    user: {
      id: 'system',
      name: 'Hệ thống',
      email: null,
    },
  };

  // Bookings integration not yet migrated to Mongo -> keep empty
  const disabledDates: Date[] = [];

  return (
    <ListingClient
      listing={serializedListing}
      currentUser={null}
      disabledDates={disabledDates}
    />
  );
}
