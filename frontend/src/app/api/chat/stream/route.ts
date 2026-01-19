import { NextResponse } from "next/server";

const PYTHON_BACKEND = process.env.PYTHON_BACKEND_URL || "http://localhost:8001";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { messages, context, useStream = true } = body;

    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json(
        { error: "Invalid request. 'messages' required." },
        { status: 400 }
      );
    }

    console.log("📡 Starting streaming chat...");

    // Call Python streaming endpoint
    const response = await fetch(`${PYTHON_BACKEND}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
      },
      body: JSON.stringify({
        messages,
        context: context || {}
      })
    });

    if (!response.ok) {
      throw new Error(`Backend error: ${response.status}`);
    }

    // Forward SSE stream to client
    const encoder = new TextEncoder();
    const decoder = new TextDecoder();

    const stream = new ReadableStream({
      async start(controller) {
        const reader = response.body?.getReader();
        if (!reader) {
          controller.close();
          return;
        }

        try {
          while (true) {
            const { done, value } = await reader.read();
            
            if (done) {
              console.log("✅ Stream complete");
              controller.close();
              break;
            }

            // Forward chunk
            controller.enqueue(value);
          }
        } catch (error) {
          console.error("❌ Stream error:", error);
          controller.error(error);
        }
      }
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
      }
    });

  } catch (error: any) {
    console.error("❌ Streaming error:", error);
    
    return NextResponse.json(
      { 
        error: "Streaming failed",
        reply: "⚠️ Không thể kết nối streaming. Hệ thống sẽ chuyển sang chế độ thường.",
        ui_type: "none"
      },
      { status: 500 }
    );
  }
}
