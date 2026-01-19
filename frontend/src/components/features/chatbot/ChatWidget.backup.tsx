"use client"

import React, { useState, useRef, useEffect } from "react"
import { MessageCircle, X, Send, Bot } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import axios from "axios"
import ReactMarkdown from "react-markdown"
import { motion, AnimatePresence } from "framer-motion"
import Link from "next/link"
import Image from "next/image"

// Định nghĩa kiểu tin nhắn
type SearchResult = {
  id: string
  title: string
  imageSrc: string
  location: string
  price: number
}

type Message = {
  role: "user" | "assistant"
  content: string
  // Nếu là tin nhắn kết quả tìm kiếm, sẽ có thêm dữ liệu này
  searchResults?: SearchResult[] 
}

const ChatWidget = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Chào bạn! Tôi là trợ lý du lịch AI. Tôi có thể giúp bạn tìm phòng, lên lịch trình hoặc giải đáp thắc mắc về du lịch. Bạn cần giúp gì không?",
    },
  ])
  
  // Tự động cuộn xuống tin nhắn mới nhất
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }
  useEffect(() => {
    scrollToBottom()
  }, [messages, isOpen])

  const handleSend = async () => {
    if (!input.trim()) return

    // 1. Thêm tin nhắn người dùng vào list
    const userMessage: Message = { role: "user", content: input }
    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      // 2. Gọi API FPT Qwen service (port 8001)
      // Đổi sang /api/nlp/chat nếu muốn dùng Ollama local (port 8000)
      const response = await axios.post("/api/nlp-fpt/chat", {
        message: userMessage.content,
        history: messages.slice(-5) // Gửi kèm 5 tin nhắn gần nhất để AI nhớ ngữ cảnh
      })

      const data = response.data

      // 3. Xử lý phản hồi từ AI
      const botMessage: Message = {
        role: "assistant",
        content: data.reply, // Câu trả lời văn bản
        searchResults: data.listings && data.listings.length > 0 ? data.listings : undefined
      }

      // Nếu AI tìm thấy khách sạn, thêm text giới thiệu
      if (botMessage.searchResults) {
        botMessage.content += "\n\nTôi tìm thấy một vài địa điểm phù hợp với yêu cầu của bạn:"
      }

      setMessages((prev) => [...prev, botMessage])

    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Xin lỗi, tôi đang gặp chút trục trặc kết nối. Vui lòng thử lại sau!" }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed bottom-4 right-4 z-100">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            className="mb-4 w-[350px] sm:w-[400px] h-[500px] bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden"
          >
            {/* Header Chat */}
            <div className="bg-blue-600 p-4 flex justify-between items-center text-white">
              <div className="flex items-center gap-2">
                <Bot className="h-6 w-6" />
                <span className="font-semibold">Travel AI Assistant</span>
              </div>
              <button onClick={() => setIsOpen(false)} className="hover:bg-blue-700 p-1 rounded">
                <X size={20} />
              </button>
            </div>

            {/* Body Chat */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl p-3 text-sm ${
                      msg.role === "user"
                        ? "bg-blue-600 text-white rounded-tr-none"
                        : "bg-white border border-gray-200 text-gray-800 rounded-tl-none shadow-sm"
                    }`}
                  >
                    {/* Nội dung văn bản */}
                    <ReactMarkdown>{msg.content}</ReactMarkdown>

                    {/* Nếu có kết quả tìm kiếm (Hotel Cards nhỏ) */}
                    {msg.searchResults && (
                      <div className="mt-3 space-y-2">
                        {msg.searchResults.map((item) => (
                          <Link key={item.id} href={`/listings/${item.id}`} className="block group">
                            <div className="bg-gray-50 rounded-lg p-2 border hover:border-blue-500 transition flex gap-3">
                              <div className="w-16 h-16 relative rounded overflow-hidden shrink-0">
                                <Image 
                                  src={item.imageSrc} 
                                  alt={item.title} 
                                  fill
                                  className="object-cover"
                                  sizes="64px"
                                />
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="font-bold text-gray-900 truncate group-hover:text-blue-600 text-xs">{item.title}</p>
                                <p className="text-gray-500 text-xs truncate">{item.location}</p>
                                <p className="text-blue-600 font-bold text-xs mt-1">
                                  {new Intl.NumberFormat('vi-VN').format(item.price)} đ
                                </p>
                              </div>
                            </div>
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-200 rounded-2xl p-3 text-sm animate-pulse">
                    Đang suy nghĩ...
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Footer Chat (Input) */}
            <div className="p-3 bg-white border-t flex gap-2">
              <Input
                id="chat-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder="Hỏi gì đó..."
                className="flex-1 focus-visible:ring-0 focus-visible:ring-offset-0"
              />
              <Button onClick={handleSend} size="icon" className="bg-blue-600 hover:bg-blue-700">
                <Send size={18} />
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Nút mở Chat */}
      <motion.button
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={() => setIsOpen(!isOpen)}
        className="bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 transition-all flex items-center justify-center"
      >
        {isOpen ? <X size={24} /> : <MessageCircle size={24} />}
      </motion.button>
    </div>
  )
}

export default ChatWidget
