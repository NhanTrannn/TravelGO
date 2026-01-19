import { NextResponse } from "next/server";

// Cấu hình URL của Python Backend - Plan-RAG Service
const PYTHON_BACKEND = process.env.PYTHON_BACKEND_URL || "http://localhost:8001";

export async function POST(req: Request) {
  try {
    // 1. Lấy dữ liệu từ Frontend gửi lên
    const body = await req.json();
    const { messages, context } = body;

    // 2. Kiểm tra dữ liệu đầu vào
    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json(
        { error: "Invalid request body. 'messages' array is required." },
        { status: 400 }
      );
    }

    // 3. Gọi sang Python Backend (Saola/Qwen)
    console.log("🔄 Forwarding chat to Python:", `${PYTHON_BACKEND}/chat`);
    
    const controller = new AbortController();
    // Set timeout 60s cho AI suy nghĩ + Web Search (có thể lâu)
    const timeoutId = setTimeout(() => controller.abort(), 60000); 

    const res = await fetch(`${PYTHON_BACKEND}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messages,
        context: context || {}, // Chuyển tiếp context để AI nhớ hội thoại
        temperature: 0.3        // Giữ nhiệt độ thấp để JSON ổn định
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // 4. Xử lý phản hồi từ Python
    if (!res.ok) {
      const errorText = await res.text();
      console.error(`❌ Python Backend Error (${res.status}):`, errorText);
      throw new Error(`Backend service failed with status ${res.status}`);
    }

    const data = await res.json();

    // 5. Trả kết quả về cho ChatWidget
    return NextResponse.json(data);

  } catch (error: any) {
    console.error("❌ API Chat Route Error:", error);

    // Xử lý timeout cụ thể
    if (error.name === 'AbortError') {
      return NextResponse.json(
        { 
          reply: "AI đang suy nghĩ hơi lâu, bạn thử hỏi lại ngắn gọn hơn nhé! 😅", 
          ui_type: "none" 
        },
        { status: 504 } // Gateway Timeout
      );
    }

    // Xử lý lỗi kết nối (Python chưa chạy)
    if (error.cause?.code === 'ECONNREFUSED') {
      return NextResponse.json(
        { 
          reply: "⚠️ Hệ thống AI chưa được bật. Vui lòng chạy Python Backend (port 8001).", 
          ui_type: "none" 
        },
        { status: 503 } // Service Unavailable
      );
    }

    return NextResponse.json(
      { error: "Internal Server Error", message: error.message },
      { status: 500 }
    );
  }
}