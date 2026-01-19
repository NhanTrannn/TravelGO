import ChatWidget from "@/components/features/chatbot/ChatWidget";
import ModalProvider from "@/lib/providers/ModalProvider";
import ToasterProvider from "@/lib/providers/ToasterProvider";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { NextAuthProvider } from "./SessionProvider";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Tour with NLP - Khám phá du lịch thông minh",
  description: "Tìm kiếm điểm đến du lịch lý tưởng bằng công nghệ xử lý ngôn ngữ tự nhiên",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        <NextAuthProvider>
          <ToasterProvider />
          <ModalProvider />
          <ChatWidget />
          {children}
        </NextAuthProvider>
      </body>
    </html>
  );
}
