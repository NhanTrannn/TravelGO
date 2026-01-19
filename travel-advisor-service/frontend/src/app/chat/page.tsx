"use client"

import React, { useState, useRef, useEffect } from "react"
import { Send, Bot, Loader2, ArrowLeft, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import ReactMarkdown from "react-markdown"
import { useRouter } from "next/navigation"

// Định nghĩa kiểu tin nhắn (copy từ ChatWidget)
type Hotel = {
  id: string
  name: string
  address: string
  priceRange: string
  rating: number
  image: string
  description?: string
  url?: string
}

type Spot = {
  id: string
  name: string
  address?: string
  description?: string
  rating?: number
  image?: string
  category?: string
}

type Message = {
  role: "user" | "assistant"
  content: string
  ui_type?: "options" | "hotel_cards" | "spot_cards" | "food_cards" | "itinerary_plan" | "itinerary" | "comprehensive" | "itinerary_builder" | "tips" | "none"
  ui_data?: {
    options?: string[]
    hotels?: Hotel[]
    spots?: (Spot | { id?: string; name: string; rating?: number; description?: string; image?: string; idx?: number; category?: string; address?: string })[]
    days?: number
    current_day?: number
    total_days?: number
    destination?: string
    items?: Array<{
      day: number
      title: string
      morning?: string
      afternoon?: string
      evening?: string
      notes?: string
    }>
    budget?: object
    actions?: Array<{label: string, action: string}>
    tips_categories?: Array<{icon: string, title: string, content: string}>
    workflow_state?: string  // State machine tracking: INITIAL | CHOOSING_SPOTS | CHOOSING_HOTEL | READY_TO_FINALIZE
    next_step_hint?: string
  }
}

export default function ChatPage() {
  const router = useRouter()
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [selectedHotels, setSelectedHotels] = useState<Set<string>>(new Set())
  const [selectedSpots, setSelectedSpots] = useState<Set<string>>(new Set())
  const [travelContext, setTravelContext] = useState({
    destination: "",
    days: "",
    budget: "",
    companions: "",
    interests: "",
    conversation_stage: "initial", // initial → planning → plan_shown → exploring_details → booking
    plan_shown: false,
    hotels_shown: false,
    selected_hotel: ""
  })
  
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load conversation từ localStorage khi mount
  useEffect(() => {
    const savedMessages = localStorage.getItem('chat_messages')
    const savedContext = localStorage.getItem('chat_context')
    
    if (savedMessages) {
      setMessages(JSON.parse(savedMessages))
    } else {
      // Tin nhắn chào mặc định
      setMessages([{
        role: "assistant",
        content: "Chào bạn! 👋 Tôi là trợ lý du lịch AI. Hãy cùng lên kế hoạch chuyến đi tuyệt vời nhé! Bạn muốn đi đâu? ✈️",
        ui_type: "none"
      }])
    }
    
    if (savedContext) {
      setTravelContext(JSON.parse(savedContext))
    }
  }, [])

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Clear chat and start new session
  const clearChat = () => {
    localStorage.removeItem('chat_messages')
    localStorage.removeItem('chat_context')
    setMessages([{
      role: "assistant",
      content: "Chào bạn! 👋 Tôi là trợ lý du lịch AI. Hãy cùng lên kế hoạch chuyến đi tuyệt vời nhé! Bạn muốn đi đâu? ✈️",
      ui_type: "none"
    }])
    setTravelContext({
      destination: "",
      days: "",
      budget: "",
      companions: "",
      interests: "",
      conversation_stage: "initial",
      plan_shown: false,
      hotels_shown: false,
      selected_hotel: ""
    })
  }

  const handleOptionClick = (option: string) => {
    handleSend(option);
  }

  // Toggle hotel selection - Auto-submit on click (single selection only)
  const toggleHotelSelection = (hotelId: string, hotelName: string) => {
    handleSend(`Tôi muốn đặt phòng tại ${hotelName}`)
  }

  // Confirm hotel selection - NOT NEEDED: Hotels auto-submit on click
  // const handleHotelConfirm = (hotels: Hotel[]) => {
  //   const selectedHotelsList = hotels.filter(h => selectedHotels.has(h.id))
  //   if (selectedHotelsList.length === 0) return
  //   
  //   const hotelNames = selectedHotelsList.map(h => h.name).join(", ")
  //   handleSend(`Tôi chọn khách sạn: ${hotelNames}`)
  //   setSelectedHotels(new Set())
  // }

  // Toggle spot selection - Allow multiple checkbox selections
  const toggleSpotSelection = (spotId: string, spotIdx: number) => {
    setSelectedSpots(prev => {
      const newSet = new Set(prev)
      if (newSet.has(spotId)) {
        newSet.delete(spotId)
      } else {
        newSet.add(spotId)
      }
      return newSet
    })
  }

  // Confirm spot selection
  const handleSpotConfirm = (spots: any[]) => {
    const selectedIndices = spots
      .map((spot, idx) => {
        const spotIdx = (spot as { idx?: number }).idx || idx + 1;
        const spotId = spot.id || String(spotIdx);
        return { spot, idx: spotIdx, spotId };
      })
      .filter(item => selectedSpots.has(item.spotId))
      .map(item => item.idx)
    
    if (selectedIndices.length === 0) return
    
    handleSend(selectedIndices.join(", "))
    setSelectedSpots(new Set())
  }

  const handleSend = async (textInput?: string) => {
    const textToSend = textInput || input;
    if (!textToSend.trim()) return;

    const userMsg: Message = { role: "user", content: textToSend }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    if (!textInput) setInput("")
    setIsLoading(true)

    try {
      const historyForApi = newMessages.slice(-10).map(m => ({
        role: m.role,
        content: m.content
      }));

      // Use streaming API - same as ChatWidget
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          messages: historyForApi,
          context: travelContext
        })
      });

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      // Handle SSE streaming response
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      
      let finalReply = "";
      let finalUiType = "none";
      let finalUiData = {};
      let newContext = { ...travelContext };

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                // Accumulate reply text (keep last non-empty)
                if (data.reply && data.reply.trim()) {
                  finalReply = data.reply;
                }
                
                // Update UI type (NEVER let 'none' overwrite existing type)
                if (data.ui_type) {
                  // Only update if we have 'none' and get something better, 
                  // OR if we get a non-'none' type (don't let 'none' overwrite)
                  if (finalUiType === 'none' && data.ui_type !== 'none') {
                    finalUiType = data.ui_type;
                  } else if (data.ui_type !== 'none') {
                    finalUiType = data.ui_type;
                  }
                  // If data.ui_type is 'none', keep existing finalUiType
                }
                
                // Update UI data (merge, never reset)
                if (data.ui_data && Object.keys(data.ui_data).length > 0) {
                  finalUiData = { ...finalUiData, ...data.ui_data };
                }
                
                // Update context from response
                if (data.context) {
                  newContext = { ...newContext, ...data.context };
                }
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              } catch (_e) {
                // Skip invalid JSON lines
              }
            }
          }
        }
      }

      // Stage transition logic
      let newStage = newContext.conversation_stage || "initial";
      
      if (finalUiType === "itinerary_plan" && !newContext.plan_shown) {
        newStage = "plan_shown";
        newContext.plan_shown = true;
      } else if (finalUiType === "hotel_cards" && !newContext.hotels_shown) {
        newStage = "exploring_hotels";
        newContext.hotels_shown = true;
      } else if (newContext.selected_hotel) {
        newStage = "hotel_selected";
      }
      
      newContext.conversation_stage = newStage;
      
      setTravelContext(newContext)
      localStorage.setItem('chat_context', JSON.stringify(newContext))
      
      const botMsg: Message = {
        role: "assistant",
        content: finalReply || "Xin lỗi, tôi không thể xử lý yêu cầu này.",
        ui_type: finalUiType as Message["ui_type"],
        ui_data: Object.keys(finalUiData).length > 0 ? finalUiData : undefined
      }
      
      const updatedMessages = [...newMessages, botMsg]
      setMessages(updatedMessages)
      localStorage.setItem('chat_messages', JSON.stringify(updatedMessages))

    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => [...prev, { 
        role: "assistant", 
        content: "⚠️ Xin lỗi, kết nối tới AI đang gặp sự cố. Vui lòng thử lại.",
        ui_type: "none"
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const renderGenUI = (msg: Message) => {
    if (!msg.ui_data || !msg.ui_type || msg.ui_type === "none") return null;

    switch (msg.ui_type) {
      case "options":
        return (
          <div className="mt-3 flex flex-wrap gap-2">
            {msg.ui_data.options?.map((opt, idx) => (
              <button
                key={idx}
                onClick={() => handleOptionClick(opt)}
                className="px-3 py-2 bg-blue-50 text-blue-700 text-sm font-medium rounded-full border border-blue-100 hover:bg-blue-100 hover:border-blue-300 transition-colors shadow-sm"
              >
                {opt}
              </button>
            ))}
          </div>
        );
      
      case "hotel_cards":
        return (
          <div className="mt-3 space-y-3">
            <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
              {msg.ui_data.hotels?.map((hotel) => {
                const isSelected = selectedHotels.has(hotel.id)
                return (
                  <div
                    key={hotel.id}
                    onClick={() => toggleHotelSelection(hotel.id, hotel.name)}
                    className={`bg-white border-2 rounded-xl overflow-hidden hover:shadow-md transition-all cursor-pointer ${
                      isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-blue-300'
                    }`}
                  >
                    <div className="flex gap-3 p-3">
                      {/* Checkbox */}
                      <div className="flex items-center">
                        <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                          isSelected ? 'bg-blue-500 border-blue-500' : 'border-gray-300'
                        }`}>
                          {isSelected && (
                            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </div>
                      </div>

                      {/* Ảnh khách sạn - compact */}
                      <div className="w-20 h-20 shrink-0 rounded-lg overflow-hidden bg-gray-100">
                        <img 
                          src={hotel.image} 
                          alt={hotel.name}
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLImageElement).src = 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800'
                          }}
                        />
                      </div>
                      
                      {/* Thông tin khách sạn */}
                      <div className="flex-1 min-w-0 flex flex-col justify-between">
                        <div>
                          <h4 className="font-bold text-sm text-gray-800 truncate">
                            {hotel.name}
                          </h4>
                          <div className="flex items-center gap-1 mt-0.5">
                            <span className="text-yellow-500 text-[10px]">⭐</span>
                            <span className="text-[11px] font-medium text-gray-700">{hotel.rating?.toFixed(1) || 'N/A'}</span>
                          </div>
                          <p className="text-[11px] text-gray-500 mt-0.5 line-clamp-1">
                            📍 {hotel.address}
                          </p>
                        </div>
                        <div className="flex items-center justify-between mt-1">
                          <p className="text-sm font-bold text-blue-600">
                            {hotel.priceRange || 'Liên hệ'}
                          </p>
                          {hotel.url && (
                            <a
                              href={hotel.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="text-[10px] px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full font-medium border border-blue-100 hover:bg-blue-100 transition-colors"
                            >
                              Chi tiết →
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
            
            {/* Nút Xác nhận - NOT NEEDED: Hotels auto-submit on click */}
            {/* {selectedHotels.size > 0 && (
              <div className="sticky bottom-0 pt-3 pb-2 bg-gradient-to-t from-gray-50 to-transparent">
                <button
                  onClick={() => handleHotelConfirm(msg.ui_data.hotels || [])}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all flex items-center justify-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Xác nhận ({selectedHotels.size} khách sạn)
                </button>
              </div>
            )} */}
          </div>
        );

      case "itinerary_plan":
      case "itinerary":
        return (
          <div className="mt-3 bg-white rounded-xl border border-blue-100 overflow-hidden shadow-sm">
            <div className="bg-blue-50/50 p-2 border-b border-blue-100 flex items-center gap-2">
              <span className="text-blue-600">🗺️</span>
              <span className="text-xs font-bold text-blue-800">
                Lịch trình: {msg.ui_data?.destination} ({msg.ui_data?.days} ngày)
              </span>
            </div>
            <div className="max-h-[300px] overflow-y-auto p-3 space-y-3">
              {msg.ui_data?.items?.map(d => (
                <div key={d.day} className="relative pl-4 border-l-2 border-blue-200">
                  <div className="absolute -left-[5px] top-0 w-2 h-2 rounded-full bg-blue-400"></div>
                  <div className="text-xs font-bold text-gray-800 mb-1">Ngày {d.day}: {d.title}</div>
                  <div className="space-y-1">
                    {d.morning && <div className="text-[11px] text-gray-600"><span className="font-semibold text-blue-600">Sáng:</span> {d.morning}</div>}
                    {d.afternoon && <div className="text-[11px] text-gray-600"><span className="font-semibold text-orange-600">Chiều:</span> {d.afternoon}</div>}
                    {d.evening && <div className="text-[11px] text-gray-600"><span className="font-semibold text-purple-600">Tối:</span> {d.evening}</div>}
                    {d.notes && <div className="text-[10px] text-gray-400 italic mt-1">{d.notes}</div>}
                  </div>
                </div>
              ))}
            </div>
            
            {/* CRITICAL FIX: Add action buttons */}
            {msg.ui_data?.actions && msg.ui_data.actions.length > 0 && (
              <div className="flex flex-wrap gap-2 p-3 pt-2 border-t border-blue-100 bg-blue-50/30">
                {msg.ui_data.actions.map((action, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(action.action)}
                    className="px-3 py-1.5 text-xs font-medium text-blue-700 bg-white border border-blue-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-all shadow-sm"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        );

      case "spot_cards":
        return (
          <div className="mt-3 space-y-2 max-h-[400px] overflow-y-auto pr-2">
            {msg.ui_data.spots?.map((spot) => (
              <div
                key={spot.id}
                onClick={() => handleOptionClick(`Xem chi tiết: ${spot.name}`)}
                className="group flex gap-3 p-2 bg-white border border-gray-200 rounded-xl hover:border-green-400 hover:shadow-md transition-all cursor-pointer"
              >
                {/* Ảnh địa điểm - compact */}
                <div className="w-16 h-16 shrink-0 rounded-lg overflow-hidden bg-gray-100">
                  <img 
                    src={spot.image || 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800'} 
                    alt={spot.name}
                    className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800'
                    }}
                  />
                </div>
                
                {/* Thông tin địa điểm */}
                <div className="flex-1 min-w-0 flex flex-col justify-center">
                  <h4 className="font-bold text-sm text-gray-800 truncate group-hover:text-green-600">
                    {spot.name}
                  </h4>
                  {spot.rating && (
                    <div className="flex items-center text-xs text-yellow-600 mt-0.5">
                      ⭐ {spot.rating.toFixed(1)}/5
                    </div>
                  )}
                  {spot.category && (
                    <span className="inline-block w-fit mt-1 text-[10px] px-2 py-0.5 bg-green-50 text-green-600 rounded-full">
                      {spot.category}
                    </span>
                  )}
                  {spot.address && (
                    <p className="text-[11px] text-gray-500 line-clamp-1 mt-0.5">
                      📍 {spot.address}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        );
      
      case "itinerary_builder": {
        const spots = msg.ui_data?.spots || [];
        const currentDay = msg.ui_data?.current_day || 1;
        const totalDays = msg.ui_data?.total_days || 3;
        
        return (
          <div className="mt-3">
            {/* Progress indicator */}
            <div className="mb-3 bg-blue-50 rounded-xl p-3 border border-blue-100">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-blue-800">
                  📅 Ngày {currentDay}/{totalDays}
                </span>
                <span className="text-[10px] text-blue-600">
                  {currentDay === totalDays ? "Ngày cuối!" : `Còn ${totalDays - currentDay} ngày`}
                </span>
              </div>
              <div className="w-full bg-blue-200 rounded-full h-1.5">
                <div 
                  className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${(currentDay / totalDays) * 100}%` }}
                />
              </div>
            </div>

            {/* Spots selection hint */}
            <p className="text-xs text-gray-600 mb-2">
              💡 Chọn các địa điểm bạn muốn đi (có thể chọn nhiều)
            </p>

            {/* Spots grid */}
            <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2 mb-3">
              {spots.map((spot, idx) => {
                const spotIdx = (spot as { idx?: number }).idx || idx + 1;
                const spotId = spot.id || String(spotIdx);
                const isSelected = selectedSpots.has(spotId);
                return (
                  <div
                    key={spot.id || idx}
                    onClick={() => toggleSpotSelection(spotId, spotIdx)}
                    className={`group flex gap-3 p-2 bg-white border-2 rounded-xl hover:shadow-md transition-all cursor-pointer ${
                      isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-blue-400'
                    }`}
                  >
                    {/* Checkbox */}
                    <div className="flex items-center">
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                        isSelected ? 'bg-blue-500 border-blue-500' : 'border-gray-300'
                      }`}>
                        {isSelected && (
                          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </div>
                    </div>

                    {/* Index badge */}
                    <div className="w-8 h-8 shrink-0 rounded-full bg-blue-100 text-blue-700 font-bold text-sm flex items-center justify-center">
                      {spotIdx}
                    </div>
                    
                    {/* Spot image */}
                    <div className="w-14 h-14 shrink-0 rounded-lg overflow-hidden bg-gray-100">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img 
                        src={spot.image || 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800'} 
                        alt={spot.name}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.target as HTMLImageElement).src = 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800'
                        }}
                      />
                    </div>
                    
                    {/* Spot info */}
                    <div className="flex-1 min-w-0 flex flex-col justify-center">
                      <h4 className="font-bold text-sm text-gray-800 truncate">
                        {spot.name}
                      </h4>
                      {spot.rating && (
                        <div className="flex items-center text-xs text-yellow-600 mt-0.5">
                          ⭐ {typeof spot.rating === 'number' ? spot.rating.toFixed(1) : spot.rating}/5
                        </div>
                      )}
                      {spot.description && (
                        <p className="text-[11px] text-gray-500 line-clamp-1 mt-0.5">{spot.description}</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Nút Xác nhận */}
            {selectedSpots.size > 0 && (
              <div className="sticky bottom-0 pt-2 pb-2 bg-gradient-to-t from-gray-50 to-transparent">
                <button
                  onClick={() => handleSpotConfirm(spots)}
                  className="w-full py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all flex items-center justify-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Xác nhận ({selectedSpots.size} địa điểm)
                </button>
              </div>
            )}
          </div>
        );
      }
      
      case "tips": {
        const categories = msg.ui_data?.tips_categories || [];
        return (
          <div className="mt-3 bg-white rounded-xl border border-yellow-100 overflow-hidden shadow-sm">
            <div className="bg-yellow-50/50 p-2 border-b border-yellow-100 flex items-center gap-2">
              <span className="text-yellow-600">💡</span>
              <span className="text-xs font-bold text-yellow-800">
                Lưu ý cho chuyến đi
              </span>
            </div>
            <div className="max-h-[300px] overflow-y-auto p-3 space-y-2">
              {categories.map((cat, idx) => (
                <div key={idx} className="flex gap-2 items-start bg-gray-50 rounded-lg p-2">
                  <span className="text-base">{cat.icon}</span>
                  <div className="flex-1">
                    <div className="text-[11px] font-bold text-gray-800 mb-0.5">{cat.title}</div>
                    <div className="text-[10px] text-gray-600">{cat.content}</div>
                  </div>
                </div>
              ))}
            </div>
            
            {/* Action buttons */}
            {msg.ui_data?.actions && msg.ui_data.actions.length > 0 && (
              <div className="flex flex-wrap gap-2 p-3 pt-2 border-t border-yellow-100 bg-yellow-50/30">
                {msg.ui_data.actions.map((action, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(action.action)}
                    className="px-3 py-1.5 text-xs font-medium text-yellow-700 bg-white border border-yellow-200 rounded-lg hover:bg-yellow-50 hover:border-yellow-300 transition-all shadow-sm"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      }
      
      default:
        return null;
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50" suppressHydrationWarning>
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10" suppressHydrationWarning>
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.back()}
              className="p-2 hover:bg-gray-100 rounded-full transition"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-full">
                <Bot className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h1 className="font-bold text-lg">Travel Assistant</h1>
                <p className="text-xs text-gray-500 flex items-center gap-1">
                  <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"/> Online (Qwen 2.5)
                </p>
              </div>
            </div>
          </div>
          {/* New Chat Button */}
          <button
            onClick={clearChat}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Cuộc trò chuyện mới
          </button>
        </div>
      </div>

      {/* Chat Area */}
      <div className="max-w-6xl mx-auto px-4 py-6">
        <div className="bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden">
          <div className="h-[calc(100vh-280px)] overflow-y-auto p-6 space-y-4">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div className="flex flex-col max-w-[80%]">
                  <div
                    className={`p-4 text-sm leading-relaxed shadow-sm ${
                      msg.role === "user"
                        ? "bg-blue-600 text-white rounded-2xl rounded-tr-sm"
                        : "bg-white text-slate-800 border border-gray-200 rounded-2xl rounded-tl-sm"
                    }`}
                  >
                    <div className="prose prose-sm max-w-none">
                      <ReactMarkdown 
                        components={{
                          ul: ({...props}) => <ul className="list-disc pl-4 my-2" {...props} />,
                          ol: ({...props}) => <ol className="list-decimal pl-4 my-2" {...props} />,
                          p: ({...props}) => <p className="my-1" {...props} />,
                          strong: ({...props}) => <strong className="font-semibold text-blue-700" {...props} />,
                          a: ({...props}) => <a target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 underline" {...props} />
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  </div>

                  {msg.role === "assistant" && renderGenUI(msg)}
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white border border-gray-200 rounded-2xl p-4 flex items-center gap-2 shadow-sm">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                  <span className="text-sm text-gray-500">AI đang suy nghĩ...</span>
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
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Hỏi về du lịch..."
                className="flex-1 h-12 px-4 text-sm"
                disabled={isLoading}
              />
              <Button 
                type="submit" 
                size="icon" 
                className={`h-12 w-12 rounded-full transition-all ${
                  input.trim() ? "bg-blue-600 hover:bg-blue-700 shadow-md" : "bg-gray-300"
                }`}
                disabled={!input.trim() || isLoading}
              >
                <Send size={20} className="ml-0.5" />
              </Button>
            </form>
            <p className="text-xs text-gray-400 mt-3 text-center">
              Powered by Qwen 2.5 Coder 32B via FPT AI
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
