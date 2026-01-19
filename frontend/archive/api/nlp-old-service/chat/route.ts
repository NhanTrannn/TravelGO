import { NextResponse } from "next/server"
import axios from "axios"
import prisma from "@/lib/prisma"

interface Listing {
  id: string
  title: string
  imageSrc: string
  location: string
  price: number
  description?: string | null
}

// 🆕 Hàm gọi AI để sinh câu trả lời văn bản (Generation Step) với context phong phú
async function generateResponseWithContext(
  userMessage: string,
  listings: Listing[],
  meta: { location?: string | null; price_max?: number | null; keywords?: string | null }
) {
  const contextData = listings.map((item, idx) =>
    `${idx + 1}. ${item.title}: ${item.price.toLocaleString('vi-VN')}đ/đêm - ${item.location}`
  ).join("\n");

  const avgPrice = Math.round(
    listings.reduce((sum, h) => sum + h.price, 0) / Math.max(listings.length, 1)
  );

  // Thử bắt số ngày / đêm từ câu hỏi
  const daysMatch = userMessage.match(/(\d+)\s*ngày/i);
  const nightsMatch = userMessage.match(/(\d+)\s*đêm/i);
  const days = daysMatch ? parseInt(daysMatch[1]) : undefined;
  const nights = nightsMatch ? parseInt(nightsMatch[1]) : (days ? days - 1 : undefined);

  const prompt = `
Bạn là Trợ lý Du lịch chuyên nghiệp.
Người dùng hỏi: "${userMessage}"

Hệ thống đã tìm thấy các khách sạn phù hợp trong Database:
${contextData}

Thông tin trích xuất:
- Địa điểm: ${meta.location || 'Không rõ'}
- Ngân sách tối đa mỗi đêm: ${meta.price_max ? meta.price_max.toLocaleString('vi-VN') + 'đ' : 'Không nêu'}
- Từ khóa ưu tiên: ${meta.keywords || 'Không có'}
- Giá trung bình nhóm khách sạn: ${avgPrice.toLocaleString('vi-VN')}đ/đêm
- Số ngày: ${days || 'Không rõ'} | Số đêm: ${nights || 'Không rõ'}

Nhiệm vụ của bạn:
1. Chào và xác nhận hiểu yêu cầu.
2. Chọn 1-2 khách sạn phù hợp nhất và giải thích ngắn gọn lý do chọn (vị trí / giá / phù hợp ngân sách).
3. Nếu có thông tin số ngày / đêm → lập lịch trình từng ngày dạng:
   Ngày 1: ...\n   Ngày 2: ... (gợi ý hoạt động đặc trưng địa phương)
4. Ước tính tổng chi phí phòng (giá trung bình * số đêm) + ăn uống & di chuyển (30-50% thêm).
5. Giọng văn: Thân thiện, tự nhiên, dùng emoji hợp lý (<= 6 emoji). Không liệt kê khô cứng.
6. KHÔNG bịa đặt khách sạn ngoài danh sách.

Trả lời ngắn gọn 180-250 từ, xuống dòng hợp lý.
`;

  try {
    const res = await axios.post("http://localhost:8000/chat", {
      message: prompt,
      history: []
    });
    return typeof res.data === 'object' ? res.data.reply || res.data : res.data;
  } catch {
    return "Mình đã tìm thấy vài lựa chọn phù hợp phía dưới; bạn có thể chọn một trong số đó để lên lịch trình chi tiết hơn nhé.";
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json()
    
    // 1. Gửi tin nhắn gốc để phân tích ý định (Extraction Step)
    const aiAnalyzeRes = await axios.post("http://localhost:8000/chat", {
      message: body.message,
      history: body.history
    })

    const aiData = aiAnalyzeRes.data 
    let listings: Listing[] = []
    let finalReply: string = aiData.reply; // Mặc định lấy câu trả lời gốc

    // 2. Nếu là SEARCH -> Truy vấn Database
    if (aiData.type === "search" && aiData.search_params) {
      const { location, price_max, keywords } = aiData.search_params as {
        location?: string | null
        price_max?: number | null
        keywords?: string | null
      }

      // Where điều kiện kiểu động (Prisma filter object)
      const where: {
        location?: { contains: string }
        price?: { lte: number }
        OR?: Array<{ title?: { contains: string }; description?: { contains: string } }>
      } = {}
      if (location) where.location = { contains: location }
      if (price_max) where.price = { lte: price_max }
      if (keywords) {
        where.OR = [
          { title: { contains: keywords } },
          { description: { contains: keywords } }
        ]
      }

      listings = await prisma.listing.findMany({
        where,
        take: 5,
        orderBy: { price: 'asc' },
        select: {
          id: true,
          title: true,
          imageSrc: true,
          location: true,
          price: true,
          description: true
        }
      }) as Listing[]

      if (listings.length > 0) {
        const enriched = await generateResponseWithContext(
          body.message,
          listings,
          { location, price_max, keywords }
        )
        if (typeof enriched === 'object' && enriched && 'reply' in (enriched as Record<string, unknown>)) {
          finalReply = (enriched as { reply: string }).reply
        } else {
          finalReply = enriched as string
        }
      } else {
        finalReply = "Tiếc quá, chưa có phòng phù hợp tiêu chí. Bạn thử đổi địa điểm hoặc tăng ngân sách nhé.";
      }
    }

    // 4. Trả về Frontend
    return NextResponse.json({ reply: finalReply, listings })

  } catch (error) {
    console.error("Chat API Error", error)
    return new NextResponse("Lỗi Chat Service", { status: 500 })
  }
}
