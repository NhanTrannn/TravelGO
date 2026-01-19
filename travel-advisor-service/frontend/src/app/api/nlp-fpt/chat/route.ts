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

// URL của FPT service (port 8001)
const FPT_SERVICE_URL = "http://localhost:8001"

// 🆕 Gọi Qwen 2.5 32B qua FPT service
async function callQwen(userMessage: string, systemPrompt?: string) {
  try {
    const messages = []
    if (systemPrompt) {
      messages.push({ role: "system", content: systemPrompt })
    }
    messages.push({ role: "user", content: userMessage })

    const res = await axios.post(`${FPT_SERVICE_URL}/chat`, {
      messages,
      temperature: 0.7,
      max_tokens: 1024
    }, { timeout: 30000 })

    return res.data.reply || "Xin lỗi, không nhận được phản hồi."
  } catch (error) {
    console.error("FPT Service error:", error)
    throw new Error("Không thể kết nối với FPT AI service")
  }
}

// Phân tích ý định người dùng (extraction)
async function analyzeIntent(userMessage: string) {
  const systemPrompt = `Bạn là AI phân tích ý định tìm kiếm du lịch.
Phân tích câu hỏi của người dùng và trả về JSON với format:
{
  "type": "search" | "chat" | "plan",
  "location": "tên địa điểm hoặc null",
  "price_max": số tiền tối đa mỗi đêm (VNĐ) hoặc null,
  "keywords": "từ khóa đặc biệt (view đẹp, gần biển, có hồ bơi...)" hoặc null,
  "days": số ngày dự định đi hoặc null
}

Ví dụ:
- "Tìm khách sạn Đà Lạt dưới 1 triệu" → {"type":"search","location":"Đà Lạt","price_max":1000000,"keywords":null,"days":null}
- "Đi Phú Quốc 3 ngày nên ở đâu" → {"type":"search","location":"Phú Quốc","price_max":null,"keywords":null,"days":3}
- "Du lịch Hà Nội có gì hay" → {"type":"chat","location":"Hà Nội","price_max":null,"keywords":null,"days":null}

Chỉ trả về JSON, không giải thích thêm.`

  try {
    const reply = await callQwen(userMessage, systemPrompt)
    // Parse JSON từ reply
    const jsonMatch = reply.match(/\{[\s\S]*\}/)
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0])
    }
    return { type: "chat", location: null, price_max: null, keywords: null, days: null }
  } catch {
    return { type: "chat", location: null, price_max: null, keywords: null, days: null }
  }
}

// Tạo câu trả lời dựa trên kết quả tìm kiếm
async function generateResponseWithListings(
  userMessage: string,
  listings: Listing[],
  meta: { location?: string | null; price_max?: number | null; keywords?: string | null; days?: number | null }
) {
  if (listings.length === 0) {
    return "Tiếc quá, mình chưa tìm thấy khách sạn phù hợp. Bạn thử đổi địa điểm hoặc điều chỉnh ngân sách nhé! 😊"
  }

  const contextData = listings.map((item, idx) =>
    `${idx + 1}. ${item.title}: ${item.price.toLocaleString('vi-VN')}đ/đêm - ${item.location}`
  ).join("\n")

  const avgPrice = Math.round(
    listings.reduce((sum, h) => sum + h.price, 0) / listings.length
  )

  const systemPrompt = `Bạn là Trợ lý Du lịch chuyên nghiệp, thân thiện, sử dụng SaoLa3.1.
Nhiệm vụ: Tư vấn khách sạn dựa trên kết quả tìm kiếm thực tế từ database.

Yêu cầu:
1. Chào và xác nhận hiểu yêu cầu
2. Giới thiệu 1-2 khách sạn nổi bật từ danh sách (giải thích lý do: giá tốt, vị trí đẹp...)
3. Nếu có số ngày → gợi ý lịch trình ngắn gọn từng ngày
4. Ước tính chi phí: (giá phòng × số đêm) + ăn uống/di chuyển (~30-50% thêm)
5. Văn phong: Tự nhiên, dùng emoji phù hợp (≤6 emoji)
6. Độ dài: 200-300 từ
7. TUYỆT ĐỐI KHÔNG bịa đặt khách sạn ngoài danh sách`

  const userPrompt = `Người dùng hỏi: "${userMessage}"

Kết quả tìm kiếm từ database:
${contextData}

Thông tin bổ sung:
- Địa điểm: ${meta.location || 'Không rõ'}
- Ngân sách tối đa/đêm: ${meta.price_max ? meta.price_max.toLocaleString('vi-VN') + 'đ' : 'Không giới hạn'}
- Từ khóa: ${meta.keywords || 'Không có'}
- Số ngày dự kiến: ${meta.days || 'Không rõ'}
- Giá trung bình: ${avgPrice.toLocaleString('vi-VN')}đ/đêm

Hãy tư vấn chi tiết và hấp dẫn.`

  return await callQwen(userPrompt, systemPrompt)
}

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const userMessage = body.message

    if (!userMessage) {
      return NextResponse.json({ error: "Message is required" }, { status: 400 })
    }

    // 1. Phân tích ý định
    const intent = await analyzeIntent(userMessage)
    console.log("🧠 Intent analysis:", intent)

    let listings: Listing[] = []
    let finalReply: string

    // 2. Nếu là search → truy vấn database
    if (intent.type === "search") {
      const { location, price_max, keywords } = intent

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

      console.log(`🔍 Found ${listings.length} listings`)

      // 3. Generate response với Qwen
      finalReply = await generateResponseWithListings(userMessage, listings, intent)
    } else {
      // Chat thuần túy (không search database)
      const systemPrompt = "Bạn là trợ lý du lịch thân thiện. Trả lời câu hỏi của người dùng một cách tự nhiên và hữu ích."
      finalReply = await callQwen(userMessage, systemPrompt)
    }

    return NextResponse.json({
      reply: finalReply,
      listings,
      intent,
      powered_by: "SaoLa3.1 via FPT AI"
    })

  } catch (error) {
    console.error("❌ Chat API Error:", error)
    return NextResponse.json(
      { error: "Internal server error", message: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    )
  }
}
