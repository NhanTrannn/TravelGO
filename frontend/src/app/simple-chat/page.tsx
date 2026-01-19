"use client"

import React, { useState, useRef, useEffect } from "react"
import { Send, Bot, Loader2, ArrowLeft, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import ReactMarkdown from "react-markdown"
import { useRouter } from "next/navigation"

type Message = {
  role: "user" | "assistant"
  content: string
}

export default function SimpleChatPage() {
  const router = useRouter()
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load conversation từ localStorage
  useEffect(() => {
    const saved = localStorage.getItem('simple_chat_messages')
    if (saved) {
      setMessages(JSON.parse(saved))
    } else {
      setMessages([{
        role: "assistant",
        content: "Xin chào! 👋 Tôi là trợ lý du lịch. Hỏi tôi bất cứ điều gì về du lịch nhé! Ví dụ:\n\n- Đà Lạt có gì hay?\n- Đi du lịch một mình có an toàn không?\n- Món ăn đặc sản Hội An là gì?\n- Nên đi Phú Quốc hay Nha Trang?"
      }])
    }
  }, [])

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim()) return

    const userMsg: Message = { role: "user", content: input }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setInput("")
    setIsLoading(true)

    try {
      const res = await fetch("/api/simple-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          messages: newMessages.map(m => ({ role: m.role, content: m.content }))
        })
      })

      const data = await res.json()

      if (data.error) throw new Error(data.error)

      const botMsg: Message = {
        role: "assistant",
        content: data.reply
      }
      
      const updatedMessages = [...newMessages, botMsg]
      setMessages(updatedMessages)
      localStorage.setItem('simple_chat_messages', JSON.stringify(updatedMessages))

    } catch (error) {
      console.error("Chat error:", error)
      setMessages(prev => [...prev, { 
        role: "assistant", 
        content: "⚠️ Xin lỗi, kết nối tới AI đang gặp sự cố. Vui lòng thử lại."
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleClear = () => {
    if (confirm("Xóa toàn bộ lịch sử chat?")) {
      setMessages([{
        role: "assistant",
        content: "Chat đã được reset! Hỏi tôi bất cứ điều gì về du lịch nhé! 🗺️"
      }])
      localStorage.removeItem('simple_chat_messages')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-orange-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.back()}
              className="p-2 hover:bg-gray-100 rounded-full transition"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-purple-100 to-pink-100 rounded-full">
                <Sparkles className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <h1 className="font-bold text-lg">Simple Chat</h1>
                <p className="text-xs text-gray-500 flex items-center gap-1">
                  <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"/> 
                  Tự do hỏi đáp - Không cần lập kế hoạch
                </p>
              </div>
            </div>
          </div>
          
          <button
            onClick={handleClear}
            className="px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded-lg transition"
          >
            🗑️ Xóa chat
          </button>
        </div>
      </div>

      {/* Chat Area */}
      <div className="max-w-6xl mx-auto px-4 py-6">
        <div className="bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden">
          {/* Info Banner */}
          <div className="bg-gradient-to-r from-purple-50 to-pink-50 border-b border-purple-100 p-4">
            <div className="flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-purple-900">
                  🎯 Chế độ Simple Chat - Trả lời tự do
                </p>
                <p className="text-purple-700 text-xs mt-1">
                  Endpoint này không có intent detection phức tạp. Phù hợp cho câu hỏi thông thường về du lịch, văn hóa, ẩm thực...
                </p>
              </div>
            </div>
          </div>

          <div className="h-[calc(100vh-320px)] overflow-y-auto p-6 space-y-4">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] p-4 text-sm leading-relaxed shadow-sm ${
                    msg.role === "user"
                      ? "bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-2xl rounded-tr-sm"
                      : "bg-white text-slate-800 border border-gray-200 rounded-2xl rounded-tl-sm"
                  }`}
                >
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown 
                      components={{
                        ul: ({...props}) => <ul className="list-disc pl-4 my-2" {...props} />,
                        ol: ({...props}) => <ol className="list-decimal pl-4 my-2" {...props} />,
                        p: ({...props}) => <p className="my-1" {...props} />,
                        strong: ({...props}) => <strong className="font-semibold" {...props} />,
                        a: ({...props}) => <a target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 underline" {...props} />
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white border border-gray-200 rounded-2xl p-4 flex items-center gap-2 shadow-sm">
                  <Loader2 className="h-4 w-4 animate-spin text-purple-500" />
                  <span className="text-sm text-gray-500">Đang suy nghĩ...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-6 bg-gray-50 border-t border-gray-200">
            <form 
              onSubmit={(e) => { e.preventDefault(); handleSend(); }}
              className="flex gap-3 items-center"
            >
              <Input
                id="simple-chat-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Hỏi về du lịch, văn hóa, ẩm thực..."
                className="flex-1 h-12 px-4 text-sm"
                disabled={isLoading}
              />
              <Button 
                type="submit" 
                size="icon" 
                className={`h-12 w-12 rounded-full transition-all ${
                  input.trim() ? "bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 shadow-md" : "bg-gray-300"
                }`}
                disabled={!input.trim() || isLoading}
              >
                <Send size={20} className="ml-0.5" />
              </Button>
            </form>
            <p className="text-xs text-gray-400 mt-3 text-center">
              💡 Simple Chat Mode - Không cần lập kế hoạch, chỉ hỏi đáp tự do
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
