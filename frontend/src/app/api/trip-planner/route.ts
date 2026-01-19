import { NextRequest, NextResponse } from 'next/server';

const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL || 'http://127.0.0.1:8000';

// Tăng timeout cho route này vì AI cần thời gian xử lý
export const maxDuration = 180; // 3 phút (Vercel Pro: 300s, Free: 10s)

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { messages, currentData } = body;

    // Proxy to Python service với timeout 180s
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 180000); // 180 seconds

    const response = await fetch(`${PYTHON_SERVICE_URL}/trip-planner/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages,
        currentData: currentData || {}
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`Python service error: ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error: unknown) {
    console.error('Trip planner API error:', error);
    
    // Kiểm tra nếu là timeout
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { 
          status: 'error',
          message: '⏱️ AI đang xử lý quá lâu. Vui lòng thử với yêu cầu đơn giản hơn hoặc thử lại sau.' 
        },
        { status: 408 } // Request Timeout
      );
    }
    
    return NextResponse.json(
      { 
        status: 'error',
        message: 'Không thể kết nối với AI service. Vui lòng thử lại.' 
      },
      { status: 500 }
    );
  }
}
