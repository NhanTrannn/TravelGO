import { NextRequest, NextResponse } from "next/server";

/**
 * Simple Chat API - Endpoint đơn giản cho câu hỏi tự do
 * 
 * Khác với /api/fpt-planner:
 * - KHÔNG có intent detection phức tạp
 * - KHÔNG có GenUI
 * - KHÔNG extract info
 * - Chỉ trả lời tự nhiên dựa trên kiến thức model
 * 
 * Phù hợp cho:
 * - Chitchat thông thường
 * - Hỏi đáp chung về du lịch (không cần plan)
 * - Câu hỏi về văn hóa, ẩm thực, tips
 * - Follow-up questions không cần UI
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { messages, temperature, max_tokens } = body;

    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json(
        { error: "Invalid messages format" },
        { status: 400 }
      );
    }

    console.log("💬 Simple Chat Request - Last message:", messages[messages.length - 1]?.content?.substring(0, 100));

    // Gọi Python service endpoint /simple-chat
    const response = await fetch("http://127.0.0.1:8001/simple-chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: messages.slice(-10), // Chỉ lấy 10 messages gần nhất
        temperature: temperature || 0.7,
        max_tokens: max_tokens || 512
      })
    });

    if (!response.ok) {
      throw new Error(`Python service error: ${response.statusText}`);
    }

    const data = await response.json();

    console.log(`✅ Simple Chat Response (${data.latency_seconds}s, ${data.tokens_used} tokens)`);

    return NextResponse.json({
      reply: data.reply,
      latency_seconds: data.latency_seconds,
      tokens_used: data.tokens_used,
      model: data.model,
      endpoint: "simple-chat"
    });

  } catch (error) {
    console.error("❌ Simple Chat Error:", error);
    return NextResponse.json(
      {
        reply: "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau.",
        error: error instanceof Error ? error.message : "Unknown error"
      },
      { status: 500 }
    );
  }
}
