
import CallToAction from "@/components/features/CallToAction";
import FeaturedDestinations from "@/components/features/FeaturedDestinations";
import HeroSection from "@/components/features/HeroSection";
import HowItWorks from "@/components/features/HowItWorks";
import NlpSearchBox from "@/components/features/NlpSearchBox";
import { mapProvinceToCard, mapSpotToCard } from "@/lib/adapters/destinationAdapter";
import { CardItem } from "@/types/ui";

// Force dynamic rendering for this page (fetches from external API)
export const dynamic = 'force-dynamic';

export default async function Home() {
  // Fetch both provinces and spots, then convert to unified CardItem format
  let items: CardItem[] = [];

  try {
    const PYTHON_BACKEND = process.env.BACKEND_ORIGIN || 'http://localhost:8001';

    // Parallel fetch: 3 featured provinces + 6 featured spots
    const [provincesRes, spotsRes] = await Promise.all([
      fetch(`${PYTHON_BACKEND}/api/provinces/featured?limit=3`, {
        cache: 'no-store',
        headers: { 'Accept': 'application/json' }
      }),
      fetch(`${PYTHON_BACKEND}/api/spots/featured?limit=6`, {
        cache: 'no-store',
        headers: { 'Accept': 'application/json' }
      })
    ]);

    // Process provinces
    if (provincesRes.ok) {
      const provincesData = await provincesRes.json();
      const provinceCards = provincesData.provinces?.map(mapProvinceToCard) || [];
      items.push(...provinceCards);
      console.log('✅ Fetched provinces:', provinceCards.length);
    } else {
      console.warn('⚠️ Failed to fetch provinces:', provincesRes.statusText);
    }

    // Process spots
    if (spotsRes.ok) {
      const spotsData = await spotsRes.json();
      const spotCards = spotsData.spots?.map(mapSpotToCard) || [];
      items.push(...spotCards);
      console.log('✅ Fetched spots:', spotCards.length);
    } else {
      console.warn('⚠️ Failed to fetch spots:', spotsRes.statusText);
    }

    // Shuffle for variety (optional)
    items = items.sort(() => Math.random() - 0.5);

  } catch (error) {
    console.error('❌ Error fetching destinations:', error);
    // Empty items will show "Chưa có điểm đến nào" message
  }

  return (
    <main className="min-h-screen">
      <HeroSection />
      <div className="container mx-auto -mt-16 relative z-10">
        <NlpSearchBox />
      </div>
      <FeaturedDestinations
        items={items}
        title="Khám phá Việt Nam"
        subtitle="Các tỉnh thành và địa điểm du lịch nổi bật"
      />
      <HowItWorks />
      <CallToAction />
    </main>
  );
}
