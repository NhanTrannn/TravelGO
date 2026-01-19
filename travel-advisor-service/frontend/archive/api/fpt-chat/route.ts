import { NextResponse } from "next/server";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    
    // Gọi sang Python Service (FPT Qwen) đang chạy ở port 8001
    const res = await fetch("http://127.0.0.1:8001/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messages: body.messages, // Truyền lịch sử chat
        temperature: 0.7,        // Tùy chỉnh độ sáng tạo
        max_tokens: 1024         // Giới hạn độ dài
      }),
    });

    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail || "Lỗi từ Python Service");
    }

    const data = await res.json();
    
    // Log để debug
    console.log(`✅ FPT Response: ${data.reply?.substring(0, 100)}... | Tokens: ${data.tokens_used} | Latency: ${data.latency_seconds}s`);
    
    return NextResponse.json(data);

  } catch (error) {
    console.error("❌ Proxy Error:", error);
    return NextResponse.json(
      { error: "Không thể kết nối tới dịch vụ AI. Đảm bảo Python service đang chạy tại port 8001." },
      { status: 500 }
    );
  }
}
