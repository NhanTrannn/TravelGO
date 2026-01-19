import TripPlannerChat from '@/components/features/TripPlannerChat';

export default function TripPlannerPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 py-12 px-4">
      <div className="container mx-auto max-w-5xl">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-3">
            ✈️ AI Travel Planner
          </h1>
          <p className="text-gray-600 text-lg">
            Để AI giúp bạn lên kế hoạch du lịch hoàn hảo trong vài phút!
          </p>
        </div>
        
        <TripPlannerChat />
        
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>💡 AI sẽ hỏi bạn từng câu một để tạo lịch trình phù hợp nhất</p>
          <p>🤖 Powered by Ollama Local LLM</p>
        </div>
      </div>
    </div>
  );
}
