import NextAuth, { AuthOptions } from "next-auth"
import CredentialsProvider from "next-auth/providers/credentials"
import dbConnect from "@/lib/db"
import User from "@/models/User"
import bcrypt from "bcrypt"

export const authOptions: AuthOptions = {
  providers: [
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          throw new Error("Dữ liệu không hợp lệ")
        }

        // Kết nối MongoDB
        await dbConnect();

        // 1. Tìm người dùng bằng Mongoose
        const user = await User.findOne({ email: credentials.email });

        if (!user || !user?.password) {
          throw new Error("Người dùng không tồn tại hoặc chưa đặt mật khẩu")
        }

        // 2. So sánh mật khẩu
        const isCorrectPassword = await bcrypt.compare(
          credentials.password,
          user.password
        )

        if (!isCorrectPassword) {
          throw new Error("Mật khẩu không chính xác")
        }

        // 3. Trả về user nếu thành công
        return {
          id: user._id.toString(),
          name: user.name,
          email: user.email,
          image: user.image
        }
      },
    }),
  ],
  debug: process.env.NODE_ENV === "development",
  session: {
    strategy: "jwt",
  },
  secret: process.env.NEXTAUTH_SECRET,
  pages: {
    signIn: "/auth/signin",
  },
}

const handler = NextAuth(authOptions)
export { handler as GET, handler as POST }
