import { NextResponse } from "next/server";

const PYTHON_BACKEND = process.env.PYTHON_BACKEND_URL || "http://localhost:8001";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { message } = body;

    // Gọi sang Python endpoint /chat nhưng với system prompt đặc biệt để chỉ lấy JSON
    const res = await fetch(`${PYTHON_BACKEND}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: [{ role: "user", content: message }],
        // Context đặc biệt để báo hiệu cho MasterController chỉ trích xuất thông tin
        context: { is_analysis_only: true }, 
        temperature: 0.1
      }),
    });

    if (!res.ok) throw new Error("Backend error");
    
    const data = await res.json();
    console.log("🔍 Analyze Result:", JSON.stringify(data.context, null, 2));
    // Python trả về format { reply, context: { ...extracted_info... } }
    // Ta lấy thông tin đã trích xuất từ context
    const analysis = {
        intent: data.context?.last_intent || "chat",
        destination: data.context?.destination,
        budget: data.context?.budget,
        days: data.context?.days,
        keywords: data.context?.preferences?.keywords || []
    };

    return NextResponse.json(analysis);

  } catch (error) {
    console.error("Analyze API Error:", error);
    return NextResponse.json({ intent: "search_hotel" }, { status: 500 }); // Fallback
  }
}