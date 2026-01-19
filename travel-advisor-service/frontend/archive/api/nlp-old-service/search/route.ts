import { NextResponse } from "next/server"
import axios from "axios"

export async function POST(request: Request) {
  try {
    const body = await request.json()
    
    // Gọi sang Python Service (đang chạy ở port 8000)
    const response = await axios.post("http://localhost:8000/analyze", {
      text: body.query,
    })

    // Trả JSON đã phân tích về cho Frontend
    return NextResponse.json(response.data)
    
  } catch (error) {
    console.error("NLP Error:", error)
    return new NextResponse("AI Service Error", { status: 500 })
  }
}
