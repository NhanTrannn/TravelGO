import bcrypt from "bcrypt"
import { NextResponse } from "next/server"
import dbConnect from "@/lib/db"
import User from "@/models/User"

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const { email, name, password } = body

    if (!email || !name || !password) {
      return new NextResponse("Thiếu thông tin (email, name, password)", { status: 400 })
    }

    // 0. Kết nối MongoDB (Mongoose)
    await dbConnect()

    // 1. Kiểm tra email đã tồn tại
    const existing = await User.findOne({ email })
    if (existing) {
      return new NextResponse("Email đã được sử dụng", { status: 409 })
    }

    // 2. Mã hóa mật khẩu
    const hashedPassword = await bcrypt.hash(password, 12)

    // 3. Tạo người dùng mới bằng Mongoose
    const user = await User.create({
      email,
      name,
      password: hashedPassword,
    })

    // 3. Trả về thông tin user vừa tạo (không trả password)
    return NextResponse.json({
      id: String(user._id),
      name: user.name,
      email: user.email,
      createdAt: user.createdAt,
    })

  } catch (error: unknown) {
    console.error("REGISTER_ERROR", error)
    return new NextResponse("Lỗi máy chủ nội bộ", { status: 500 })
  }
}
