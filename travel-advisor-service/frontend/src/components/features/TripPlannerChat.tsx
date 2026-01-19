"use client";

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Sparkles } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  ui_type?: 'text' | 'budget_selection' | 'travelers_selection';
  current_field?: string;
}

interface TripData {
  destination?: string;
  duration?: number;
  budget?: 'economical' | 'moderate' | 'luxury';
  travelers?: 'solo' | 'couple' | 'family' | 'group';
}

const BUDGET_OPTIONS = [
  { value: 'economical', label: 'Tiết kiệm 💰', emoji: '💰' },
  { value: 'moderate', label: 'Trung bình 💵', emoji: '💵' },
  { value: 'luxury', label: 'Sang trọng 💎', emoji: '💎' },
];

const TRAVELERS_OPTIONS = [
  { value: 'solo', label: 'Một mình 🧳', emoji: '🧳' },
  { value: 'couple', label: 'Cặp đôi 💑', emoji: '💑' },
  { value: 'family', label: 'Gia đình 👨‍👩‍👧‍👦', emoji: '👨‍👩‍👧‍👦' },
  { value: 'group', label: 'Nhóm bạn 👥', emoji: '👥' },
];

export default function TripPlannerChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Xin chào! Mình là trợ lý lập kế hoạch du lịch AI. Bạn muốn đi du lịch ở đâu? 🌏✨',
      ui_type: 'text',
      current_field: 'destination'
    }
  ]);
  const [tripData, setTripData] = useState<TripData>({});
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text: string, fieldValue?: string | number) => {
    if (!text.trim() && !fieldValue) return;

    // Add user message
    const userMsg: Message = { 
      role: 'user', 
      content: text 
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      // Call Next.js API (proxy to Python)
      const response = await fetch('/api/trip-planner', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, userMsg],
          currentData: tripData
        })
      });

      const data = await response.json();

      if (data.status === 'complete') {
        // ✅ Đã đủ thông tin → Hiện loading và chuyển trang
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: '🎉 Đã xong! Đang tạo lịch trình chi tiết cho bạn... Vui lòng đợi 30-60 giây.',
          ui_type: 'text'
        }]);
        
        // Delay nhỏ để user thấy message trước khi redirect
        setTimeout(() => {
          const queryParams = new URLSearchParams({
            data: JSON.stringify(data)
          }).toString();
          window.location.href = `/trip-result?${queryParams}`;
        }, 1000);
        
      } else if (data.status === 'error') {
        // ❌ Lỗi
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.message || 'Có lỗi xảy ra. Vui lòng thử lại.',
          ui_type: 'text'
        }]);
      } else {
        // 🔄 Hỏi tiếp
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.message,
          ui_type: data.ui_type,
          current_field: data.current_field
        }]);

        // Cập nhật tripData nếu có field mới
        if (fieldValue && data.current_field) {
          setTripData(prev => ({
            ...prev,
            [data.current_field]: fieldValue
          }));
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '⚠️ Không thể kết nối với server. Vui lòng thử lại.',
        ui_type: 'text'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      sendMessage(input);
    }
  };

  return (
    <div className="flex flex-col h-[600px] max-w-3xl mx-auto bg-white rounded-lg shadow-xl overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4 flex items-center gap-3">
        <Sparkles className="w-6 h-6" />
        <div>
          <h2 className="text-xl font-bold">AI Travel Planner</h2>
          <p className="text-sm opacity-90">Lập kế hoạch du lịch thông minh</p>
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
              msg.role === 'user' 
                ? 'bg-blue-500 text-white rounded-br-none' 
                : 'bg-white text-gray-800 rounded-bl-none shadow-md'
            }`}>
              <p className="whitespace-pre-wrap">{msg.content}</p>

              {/* 🎯 GENERATIVE UI - Budget Selection */}
              {msg.ui_type === 'budget_selection' && (
                <div className="grid grid-cols-3 gap-2 mt-3">
                  {BUDGET_OPTIONS.map(opt => (
                    <button
                      key={opt.value}
                      onClick={() => sendMessage(opt.label, opt.value)}
                      className="px-4 py-3 bg-gradient-to-br from-blue-50 to-purple-50 hover:from-blue-100 hover:to-purple-100 rounded-xl border-2 border-blue-200 hover:border-blue-400 transition-all font-medium text-sm flex flex-col items-center gap-1"
                    >
                      <span className="text-2xl">{opt.emoji}</span>
                      <span>{opt.label.replace(opt.emoji, '').trim()}</span>
                    </button>
                  ))}
                </div>
              )}

              {/* 🎯 GENERATIVE UI - Travelers Selection */}
              {msg.ui_type === 'travelers_selection' && (
                <div className="grid grid-cols-2 gap-2 mt-3">
                  {TRAVELERS_OPTIONS.map(opt => (
                    <button
                      key={opt.value}
                      onClick={() => sendMessage(opt.label, opt.value)}
                      className="px-4 py-3 bg-gradient-to-br from-green-50 to-teal-50 hover:from-green-100 hover:to-teal-100 rounded-xl border-2 border-green-200 hover:border-green-400 transition-all font-medium text-sm flex flex-col items-center gap-1"
                    >
                      <span className="text-2xl">{opt.emoji}</span>
                      <span>{opt.label.replace(opt.emoji, '').trim()}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white rounded-2xl px-4 py-3 shadow-md rounded-bl-none">
              <div className="flex items-center gap-2 mb-2">
                <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                <span className="text-gray-600 font-medium">AI đang xử lý...</span>
              </div>
              <p className="text-xs text-gray-500">
                ⏱️ Có thể mất 30-60 giây nếu đang tạo lịch trình chi tiết
              </p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="p-4 bg-white border-t border-gray-200">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Nhập câu trả lời của bạn..."
            disabled={isLoading}
            className="flex-1 px-4 py-3 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-6 py-3 bg-blue-500 text-white rounded-full hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
