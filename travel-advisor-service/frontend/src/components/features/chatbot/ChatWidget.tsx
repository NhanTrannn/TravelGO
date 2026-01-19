"use client"

/**
 * ChatWidget Component - Travel Planning Chatbot
 *
 * CRITICAL: Context Preservation
 * ================================
 * This component maintains conversation context (travelContext) which includes:
 * - destination, days, budget, etc. (user travel info)
 * - itinerary_builder (interactive itinerary state)
 * - workflow_state (state machine position)
 * - spot_selector_state (optional multi-choice selection)
 *
 * Context is:
 * 1. Updated from API response: chunk.context or data.context
 * 2. Passed to next API request: body.context
 * 3. Persisted in localStorage for session continuity
 *
 * The context MUST be passed in every request to maintain:
 * - Interactive itinerary builder state (spots, days, etc.)
 * - User's spot selections across multiple days
 * - Hotel selections and pricing
 *
 * Without context, each request starts fresh and loses:
 * - Previous spot selections
 * - Current day in itinerary
 * - Available spots list (causing "no images" on Day 2+)
 *
 * FIX Applied (2025-01-06):
 * - Added logging to track context passing
 * - Verified context update in both streaming and regular API
 * - Backend now populates available_spots with full image data
 *
 * NEW (2026-01-16):
 * - Added SpotSelectorTable for optional multi-choice spot selection
 * - Added verification message display for itinerary auto-fixes
 */

import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { AnimatePresence, motion } from "framer-motion"
import { Bot, Calendar, Loader2, MapPin, Maximize2, MessageCircle, Minimize2, RefreshCw, Send, Sparkles, X } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import ReactMarkdown from "react-markdown"
import SpotSelectorTable from "./SpotSelectorTable"

// --- TYPES ---
type Hotel = {
  id: string
  name: string
  address: string
  priceRange?: string
  price_formatted?: string  // Backend alternative field
  price_display?: string    // Backend alternative field
  rating: number
  image: string
  description?: string
  url?: string  // Optional booking URL
}

type Spot = {
  id?: string
  name?: string
  label?: string  // For backward compatibility
  value?: string  // For backward compatibility
  description?: string
  rating?: number
  image?: string
  address?: string
  cost?: string
  tags?: string[]
  confidence?: number
}

type ItineraryItem = {
  day: number
  title: string
  morning?: string
  afternoon?: string
  evening?: string
  notes?: string
}

type Message = {
  role: "user" | "assistant"
  content: string
  ui_type?: "options" | "hotel_cards" | "itinerary_plan" | "itinerary" | "itinerary_display" | "spot_cards" | "food_cards" | "comprehensive" | "itinerary_builder" | "tips" | "spot_selector_table" | "spot_selector_update" | "distance_info" | "month_selector" | "none"
  ui_data?: {
    options?: (string | Spot)[]
    hotels?: Hotel[]
    food?: Array<{id?: string; name: string; type?: string; description?: string; dishes?: string[]; image?: string; rating?: number; address?: string; cost?: string}>
    spots?: Array<{id?: string; name: string; rating?: number; description?: string; image?: string; idx?: number}>
    // Load-more support
    all_spots?: Array<{id?: string; name: string; rating?: number; description?: string; image?: string; idx?: number}>
    show_load_more_button?: boolean
    load_more_text?: string
    has_more_spots?: boolean
    total_available_spots?: number
    title?: string
    days?: number
    current_day?: number
    total_days?: number
    duration?: number
    destination?: string
    items?: ItineraryItem[]
    actions?: Array<{label: string; action: string}>  // Action buttons for next steps
    tips_categories?: Array<{icon: string; title: string; content: string}>  // Tips with categories
    // Spot Selector Table fields
    columns?: string[]
    rows?: Array<{id: string; name: string; category: string; rating: number; best_time: string[]; avg_duration_min: number; area: string; image?: string; description?: string}>
    default_selected_ids?: string[]
    // Distance Info fields
    hotel?: string
    distances?: Array<{name: string; distance_km: number; address: string; image?: string}>
    // Auto-generated itinerary display
    itinerary?: {
      location?: string
      duration?: number
      start_date?: string
      people_count?: number
      budget?: number
      estimated_cost?: number
      reasoning?: string
      hotels?: Array<{
        id?: string
        name?: string
        rating?: number
        price?: string | number
        address?: string
        image?: string
      }>
      days?: Array<{
        day: number
        spots?: Array<{
          id?: string
          name?: string
          session?: string
          category?: string
          rating?: number
          image?: string
        }>
      }>
    }
  }
}

type TravelContext = {
  destination: string
  days: string
  budget: string
  companions: string
  interests: string
  destination_slug: string
  [key: string]: unknown  // Allow additional properties from API
}

type ChatWidgetProps = {
  initialDestination?: string
}

// Session storage key for persistence
const CHAT_SESSION_KEY = 'saola_chat_session';

// Helper functions for session persistence
const loadSession = () => {
  if (typeof window === 'undefined') return null;
  try {
    const saved = localStorage.getItem(CHAT_SESSION_KEY);
    if (saved) {
      const session = JSON.parse(saved);
      // Only restore if session is less than 24 hours old
      if (session.timestamp && Date.now() - session.timestamp < 24 * 60 * 60 * 1000) {
        return session;
      }
    }
  } catch (e) {
    console.error('Failed to load chat session:', e);
  }
  return null;
};

const saveSession = (messages: Message[], context: Record<string, unknown>) => {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(CHAT_SESSION_KEY, JSON.stringify({
      messages,
      context,
      timestamp: Date.now()
    }));
  } catch (e) {
    console.error('Failed to save chat session:', e);
  }
};

const clearSession = () => {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(CHAT_SESSION_KEY);
  } catch (e) {
    console.error('Failed to clear chat session:', e);
  }
};

const defaultGreeting: Message = {
  role: "assistant",
  content: "Chào bạn! 👋 Tôi là trợ lý du lịch SaoLa AI. Tôi có thể giúp bạn lên lịch trình, tìm khách sạn và gợi ý điểm đến hấp dẫn. Bạn muốn đi đâu? ✈️",
  ui_type: "none"
};

const ChatWidget = ({ initialDestination }: ChatWidgetProps = {}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [selectedHotels, setSelectedHotels] = useState<Set<string>>(new Set())
  // Global (legacy) selection, used by some UI types
  const [selectedSpots, setSelectedSpots] = useState<Set<string>>(new Set())
  // Per-day selection for itinerary_builder to avoid cross-day interference
  const [selectedSpotsByDay, setSelectedSpotsByDay] = useState<Record<number, Set<string>>>({})

  // Initialize from session storage
  const [messages, setMessages] = useState<Message[]>(() => {
    const session = loadSession();
    return session?.messages?.length > 0 ? session.messages : [defaultGreeting];
  })

  const defaultContext: TravelContext = {
    destination: "",
    days: "",
    budget: "",
    companions: "",
    interests: "",
    destination_slug: ""
  };

  // Context quản lý trạng thái chuyến đi - also from session
  const [travelContext, setTravelContext] = useState<TravelContext>(() => {
    const session = loadSession();
    return session?.context ? { ...defaultContext, ...session.context } : defaultContext;
  })

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [hasAutoSent, setHasAutoSent] = useState(false)

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isOpen, isLoading])

  // Save session whenever messages or context change
  useEffect(() => {
    if (messages.length > 1 || travelContext.destination) {
      saveSession(messages, travelContext);
    }
  }, [messages, travelContext])

  // Toggle hotel selection - Auto-submit on click (single selection only)
  const toggleHotelSelection = (hotelId: string, hotelName: string) => {
    handleSend(`Tôi muốn đặt phòng tại ${hotelName}`)
  }

  // Confirm hotel selection
  // COMMENTED: Auto-submit on checkbox click instead of manual confirm button
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
        const s = spot as Spot & { idx?: number };
        const spotIdx = s.idx || idx + 1;
        const spotId = s.id || String(spotIdx);
        return { spot, idx: spotIdx, spotId };
      })
      .filter(item => selectedSpots.has(item.spotId))
      .map(item => item.idx)

    if (selectedIndices.length === 0) return

    handleSend(selectedIndices.join(", "))
    setSelectedSpots(new Set())
  }

  // Function to clear chat and start new conversation
  const handleNewConversation = () => {
    clearSession();
    setMessages([defaultGreeting]);
    setTravelContext(defaultContext);
    setHasAutoSent(false);
    setSelectedHotels(new Set());
    setSelectedSpots(new Set());
    setSelectedSpotsByDay({});
  }

  // --- AUTO-SEND INITIAL DESTINATION ---
  useEffect(() => {
    if (initialDestination && !hasAutoSent && messages.length === 1) {
      setHasAutoSent(true)
      setIsOpen(true) // Mở chat ngay khi có context

      const destName = initialDestination
        .split('-')
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ')

      // Update context ngay lập tức
      setTravelContext(prev => ({
          ...prev,
          destination: destName,
          destination_slug: initialDestination
      }))

      // Gửi tin nhắn giả lập từ user
      const msg = `Tôi muốn đi du lịch ${destName}`;
      handleSend(msg);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialDestination])

  // --- HANDLE OPTION CLICK ---
  const handleOptionClick = (option: string | Spot) => {
    const text = typeof option === 'string' ? option : (option.label || option.name || "");

    // Logic gửi tin nhắn tự nhiên hơn
    let messageToSend = text;

    // Nếu là chọn địa điểm/khách sạn cụ thể
    if (typeof option !== 'string' || text?.startsWith("Chọn")) {
        messageToSend = `Tôi quan tâm đến ${text}. Hãy cho tôi thêm thông tin chi tiết.`;
    }
    // Nếu là option ngắn (Budget, Days...)
    else if (text && text.length < 20) {
        // Giữ nguyên để AI parse dễ
        messageToSend = text;
    }

    handleSend(messageToSend);
  }

  // --- MAIN SEND FUNCTION ---
  const handleSend = async (textInput?: string) => {
    const textToSend = textInput || input;
    if (!textToSend.trim()) return;

    // Frontend-only: Expand spots list when user clicks "Xem thêm" without calling backend
    if (textToSend.trim().toLowerCase() === "xem thêm") {
      const lastIndex = [...messages].map((m, i) => ({ m, i }))
        .reverse()
        .find(item => item.m.role === "assistant" && item.m.ui_type === "itinerary_builder")?.i;

      const lastBotMsg = typeof lastIndex === "number" ? messages[lastIndex] : undefined;
      const allSpots = lastBotMsg?.ui_data?.all_spots;

      if (typeof lastIndex === "number" && allSpots && Array.isArray(allSpots) && allSpots.length > 0) {
        const updatedMsg: Message = {
          role: "assistant",
          content: lastBotMsg!.content || "",
          ui_type: "itinerary_builder",
          ui_data: {
            ...(lastBotMsg!.ui_data || {}),
            spots: allSpots,
            show_load_more_button: false,
            has_more_spots: false,
            total_available_spots: allSpots.length
          }
        };

        setMessages(prev => {
          const next = [...prev];
          next[lastIndex] = updatedMsg;
          return next;
        });
        setIsLoading(false);
        if (!textInput) setInput("");
        return;
      }
    }

    // 1. UI Updates ngay lập tức
    const userMsg: Message = { role: "user", content: textToSend }
    setMessages(prev => [...prev, userMsg])
    if (!textInput) setInput("")
    setIsLoading(true)

    try {
      // 2. Chuẩn bị payload
      const historyForApi = messages.slice(-6).map(m => ({
        role: m.role,
        content: m.content
      }));
      historyForApi.push({ role: "user", content: userMsg.content });

      // 3. Gọi STREAMING API
      console.log("📤 Sending request with context:", {
        itinerary_builder: travelContext.itinerary_builder ? "✅ Present" : "❌ Missing",
        contextKeys: Object.keys(travelContext)
      });

      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: historyForApi,
          context: travelContext
        })
      });

      if (!res.ok) {
        // Fallback to regular API if streaming fails
        console.warn("⚠️ Streaming failed, using regular API");
        return handleSendRegular(historyForApi);
      }

      // 4. Process SSE Stream
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error("No reader available");
      }

      let buffer = "";
      let messageIndex = messages.length + 1; // Index for progressive messages

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        // Decode chunk
        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || ""; // Keep incomplete line in buffer

        for (const line of lines) {
          if (!line.trim() || !line.startsWith("data: ")) continue;

          const data = line.substring(6); // Remove "data: " prefix

          if (data === "[DONE]") {
            console.log("✅ Streaming complete");
            continue;
          }

          try {
            const chunk = JSON.parse(data);

            // Skip if chunk is null or invalid
            if (!chunk || typeof chunk !== 'object') {
              console.warn("⚠️ Received invalid chunk:", chunk);
              continue;
            }

            // DEBUG: Log all chunks to see what backend sends
            console.log("📦 Received chunk:", {
              status: chunk.status,
              ui_type: chunk.ui_type,
              has_reply: !!chunk.reply,
              reply_preview: chunk.reply?.substring(0, 100),
              has_context: !!chunk.context,
              has_ui_data: !!chunk.ui_data
            });

            // Update context if provided (IMPORTANT: do this BEFORE skipping empty messages)
            if (chunk.context) {
              console.log("🔄 Updating context:", chunk.context);
              setTravelContext(prev => ({ ...prev, ...chunk.context }));
            }

            // Skip empty complete messages (just signals end) but AFTER updating context
            if (chunk.status === "complete" && !chunk.reply?.trim()) {
              console.log("✅ Stream complete signal received");
              continue;
            }

            // Add or update message progressively
            const botMsg: Message = {
              role: "assistant",
              content: chunk.reply || "",
              ui_type: chunk.ui_type || "none",
              ui_data: chunk.ui_data
            };

            // Only add/update if there's actual content
            if (botMsg.content.trim() || botMsg.ui_data) {
              setMessages(prev => {
                // ALWAYS add partial chunks as new messages to show all sections
                // This ensures spots, hotels, food, etc. are all displayed
                if (chunk.status === "partial") {
                  return [...prev, botMsg];
                } else if (chunk.status === "complete" || chunk.status === "success") {
                  // FIX: Always add complete messages if they have content
                  // Only skip completely empty completion signals
                  if (botMsg.content.trim() || botMsg.ui_data) {
                    console.log("📝 Adding complete message:", botMsg.content.substring(0, 100));
                    return [...prev, botMsg];
                  }
                  return prev;
                } else {
                  // Unknown status - add if has content
                  return [...prev, botMsg];
                }
              });
            }

          } catch (e) {
            console.error("Failed to parse SSE chunk:", e, "Data:", data);
            // Continue processing other chunks even if one fails
            continue;
          }
        }
      }

    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "⚠️ Hệ thống đang bận. Vui lòng thử lại sau giây lát.",
        ui_type: "none"
      }])
    } finally {
      setIsLoading(false)
    }
  }

  // --- FALLBACK: Regular API (non-streaming) ---
  const handleSendRegular = async (historyForApi: Array<{role: string, content: string}>) => {
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: historyForApi,
          context: travelContext
        })
      });

      if (!res.ok) throw new Error(`API Error: ${res.status}`);
      const data = await res.json();

      // Update Context
      if (data.context) {
        setTravelContext(prev => {
          const next = { ...prev, ...data.context };
          console.log("🔄 Context Updated:", next);
          return next;
        });
      }

      // Add bot response
      const botMsg: Message = {
        role: "assistant",
        content: data.reply || "Xin lỗi, tôi chưa hiểu ý bạn.",
        ui_type: data.ui_type || "none",
        ui_data: data.ui_data
      }

      setMessages(prev => [...prev, botMsg])

    } catch (error) {
      console.error("Regular API error:", error);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "⚠️ Không thể kết nối server.",
        ui_type: "none"
      }])
    }
  }

  // --- HELPER: Render action buttons ---
  const renderActionButtons = (actions: Array<{label: string, action: string}> | undefined) => {
    if (!actions || actions.length === 0) return null;

    const handleAction = (action: string) => {
      // Map action to user message
      const actionMessages: Record<string, string> = {
        "more_spots": "Xem thêm địa điểm",
        "more_hotels": "Xem thêm khách sạn",
        "more_food": "Xem thêm quán ăn",
        "find_hotels": "Tìm khách sạn",
        "find_spots": "Tìm địa điểm",
        "plan_trip": "Lên lịch trình cho tôi",
        "compare_prices": "So sánh giá khách sạn",
        "calculate_cost": "Tính chi phí chuyến đi"
      };

      const message = actionMessages[action] || action;
      handleSend(message);
    };

    return (
      <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-gray-100">
        {actions.map((a, idx) => (
          <button
            key={idx}
            onClick={() => handleAction(a.action)}
            className="px-3 py-1.5 bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 text-xs font-medium rounded-full border border-blue-200 hover:from-blue-100 hover:to-indigo-100 hover:border-blue-300 transition-all shadow-sm"
          >
            {a.label}
          </button>
        ))}
      </div>
    );
  };

  // --- RENDER GEN UI COMPONENTS ---
  const renderGenUI = (msg: Message) => {
    if (!msg.ui_data || !msg.ui_type || msg.ui_type === "none") return null;

    const { ui_data } = msg;

    try {
      switch (msg.ui_type) {
      // 1. Dạng nút bấm hoặc thẻ địa điểm
      case "options":
      case "spot_cards": {
        const mixed = (ui_data.spots ?? ui_data.options ?? []) as Array<string | Spot>;

        const textOptions = mixed.filter((x): x is string => typeof x === "string");
        const spotOptions = mixed.filter(
          (x): x is Spot => typeof x === "object" && x !== null
        );

        if (textOptions.length === 0 && spotOptions.length === 0) return null;

        return (
          <motion.div initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} className="mt-3 w-full">
            {ui_data.title && (
              <div className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">
                {ui_data.title}
              </div>
            )}

            {/* Cards cho Spot objects */}
            {spotOptions.length > 0 && (
              <div className="grid grid-cols-1 gap-2 max-h-[320px] overflow-y-auto pr-1 scrollbar-thin">
                {spotOptions.map((s, idx) => {
                  const spotName = s.name || s.label || "Unknown";
                  return (
                    <div
                      key={s.id || `spot-${idx}`}
                      onClick={() => handleOptionClick(s)}
                      className="group flex gap-3 p-2 bg-white border border-gray-200 rounded-xl hover:border-blue-400 hover:shadow-md transition-all cursor-pointer"
                    >
                      <div className="w-16 h-16 shrink-0 rounded-lg overflow-hidden bg-gray-100 relative">
                        <img
                          src={s.image || "https://placehold.co/100?text=No+Image"}
                          alt={spotName}
                          className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                          onError={(e) =>
                            ((e.currentTarget as HTMLImageElement).src =
                              "https://placehold.co/100?text=No+Image")
                          }
                        />
                      </div>
                      <div className="flex-1 min-w-0 flex flex-col justify-center">
                        <h4 className="font-bold text-sm text-gray-800 truncate group-hover:text-blue-600">
                          {spotName}
                        </h4>
                        {s.rating && (
                          <div className="flex items-center text-xs text-yellow-600 mt-0.5">
                            <Sparkles size={10} className="mr-1" /> {s.rating}/5
                          </div>
                        )}
                        {s.description && (
                          <p className="text-xs text-gray-500 line-clamp-1 mt-0.5">{s.description}</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Badges cho strings */}
            {textOptions.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {textOptions.map((t, idx) => (
                  <button
                    key={`opt-${idx}`}
                    onClick={() => handleOptionClick(t)}
                    className="px-3 py-1.5 bg-blue-50 text-blue-700 text-xs font-medium rounded-full border border-blue-100 hover:bg-blue-100 hover:border-blue-300 transition-colors"
                  >
                    {t}
                  </button>
                ))}
              </div>
            )}

            {renderActionButtons(ui_data.actions)}
          </motion.div>
        );
      }


      // Month selector for "chưa biết" date flow
      case "month_selector": {
        const bestMonths = ui_data.best_months || [];
        const avoidMonths = ui_data.avoid_months || [];
        const destination = ui_data.destination || "điểm đến";

        const handlePick = (label: string) => handleSend(label);

        return (
          <motion.div initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} className="mt-3 w-full bg-white border border-blue-100 rounded-xl shadow-xs">
            <div className="p-3 border-b border-blue-50 bg-blue-50/40 flex items-center gap-2 text-xs text-blue-800 font-semibold">
              <Calendar size={14} className="text-blue-600" />
              <span>Chọn tháng phù hợp cho chuyến đi {destination}</span>
            </div>

            <div className="p-3 space-y-3 text-sm text-gray-700">
              {bestMonths.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-green-700 mb-2">Tháng nên đi</div>
                  <div className="flex flex-wrap gap-2">
                    {bestMonths.map((m: string, idx: number) => (
                      <button
                        key={`best-${idx}`}
                        onClick={() => handlePick(m)}
                        className="px-3 py-1.5 bg-green-50 text-green-700 border border-green-200 rounded-full text-xs font-medium hover:bg-green-100 transition"
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {avoidMonths.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-red-700 mb-2">Tháng nên tránh</div>
                  <div className="flex flex-wrap gap-2">
                    {avoidMonths.map((m: string, idx: number) => (
                      <span
                        key={`avoid-${idx}`}
                        className="px-3 py-1.5 bg-red-50 text-red-700 border border-red-200 rounded-full text-xs font-medium"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="text-[12px] text-gray-600 bg-gray-50 border border-gray-100 rounded-lg p-2 leading-snug">
                Nhập ngày cụ thể (VD: "15/3/2026") hoặc chọn một tháng phía trên. Nếu chưa chắc, hãy gõ "gợi ý ngày" để tôi đề xuất.
              </div>
            </div>
          </motion.div>
        );
      }

      // 2. [QUAN TRỌNG] Dạng thẻ khách sạn với checkbox
      case "hotel_cards": {
        const hotels = ui_data.hotels || [];
        return (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-3 space-y-3"
          >
            <div className="grid grid-cols-1 gap-3 max-h-[400px] overflow-y-auto pr-2 scrollbar-thin">
              {hotels.map((hotel) => {
                const isSelected = selectedHotels.has(hotel.id);
                return (
                  <div
                    key={hotel.id}
                    onClick={() => toggleHotelSelection(hotel.id, hotel.name)}
                    className={`bg-white rounded-lg overflow-hidden hover:shadow-lg transition-all cursor-pointer border border-gray-200 ${
                      isSelected ? 'ring-2 ring-blue-500 shadow-lg' : 'hover:border-blue-300 hover:shadow-md'
                    }`}
                  >
                    {/* Image Section */}
                    <div className="relative h-40 bg-gray-100 overflow-hidden">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={hotel.image || 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800'}
                        alt={hotel.name}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.currentTarget as HTMLImageElement).src = 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800'
                        }}
                      />

                      {/* Rating Badge */}
                      <div className="absolute top-3 right-3 bg-white px-2.5 py-1 rounded-full flex items-center gap-1 shadow-md">
                        <span className="text-yellow-500 text-sm">⭐</span>
                        <span className="text-sm font-bold text-gray-800">{hotel.rating}/5</span>
                      </div>

                      {/* Selected Checkmark Overlay */}
                      {isSelected && (
                        <div className="absolute inset-0 bg-blue-500/20 flex items-center justify-center">
                          <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center">
                            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                            </svg>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Content Section */}
                    <div className="p-3">
                      <h4 className="font-bold text-sm text-gray-800 line-clamp-1 mb-1">
                        {hotel.name}
                      </h4>
                      <p className="text-[11px] text-gray-500 line-clamp-1 mb-2">
                        📍 {hotel.address}
                      </p>

                      {/* Price & Action Section */}
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-bold text-blue-600">
                          {hotel.priceRange || hotel.price_formatted || hotel.price_display || 'Liên hệ'}
                        </p>
                        {hotel.url && (
                          <a
                            href={hotel.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-[10px] px-2 py-1 bg-blue-50 text-blue-600 rounded-full font-medium border border-blue-100 hover:bg-blue-100 transition-colors"
                          >
                            Chi tiết →
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Action buttons */}
            {renderActionButtons(ui_data.actions)}
          </motion.div>
        );
      }

      // 3. Dạng lịch trình
      case "itinerary_plan": {
        const items = ui_data.items || [];
        return (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-3 bg-white rounded-xl border border-blue-100 overflow-hidden shadow-xs">
            <div className="bg-blue-50/50 p-2 border-b border-blue-100 flex items-center gap-2">
               <MapPin size={14} className="text-blue-600"/>
               <span className="text-xs font-bold text-blue-800">Lịch trình: {ui_data.destination} ({ui_data.days} ngày)</span>
            </div>
            <div className="max-h-[300px] overflow-y-auto p-2 space-y-3 scrollbar-thin">
              {items.map((item) => (
                <div key={item.day} className="relative pl-3 border-l-2 border-blue-200">
                  <div className="absolute -left-[5px] top-0 w-2 h-2 rounded-full bg-blue-400"></div>
                  <div className="text-xs font-bold text-gray-800 mb-1">Ngày {item.day}: {item.title}</div>
                  <div className="space-y-1">
                    {item.morning && <div className="text-[11px] text-gray-600"><span className="font-semibold text-blue-600">Sáng:</span> {item.morning}</div>}
                    {item.afternoon && <div className="text-[11px] text-gray-600"><span className="font-semibold text-orange-600">Chiều:</span> {item.afternoon}</div>}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        );
      }

      // 4. Food cards (Món ăn/Quán ăn)
      case "food_cards": {
        const foods = ui_data.food || [];
        return (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-3 space-y-2"
          >
            {foods.map((food, idx) => {
              if (food.type === 'recommendation') {
                // Display specialty dishes
                return (
                  <div
                    key={food.id || idx}
                    className="bg-gradient-to-r from-orange-50 to-amber-50 border border-orange-200 rounded-xl p-3"
                  >
                    <div className="flex items-start gap-2">
                      <span className="text-lg">🌟</span>
                      <div>
                        <h4 className="font-bold text-sm text-orange-800">{food.name}</h4>
                        {food.description && <p className="text-xs text-gray-600 mt-1">{food.description}</p>}
                        {food.dishes && food.dishes.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {food.dishes.map((dish: string, didx: number) => (
                              <span
                                key={didx}
                                className="text-xs px-2 py-0.5 bg-white text-orange-700 rounded-full border border-orange-200"
                              >
                                {dish}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              } else {
                // Display actual restaurant
                return (
                  <div
                    key={food.id || idx}
                    className="bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-md hover:border-orange-300 transition-all group"
                  >
                    <div className="flex gap-3 p-3">
                      {food.image && (
                        <div className="w-20 h-20 shrink-0 rounded-lg overflow-hidden bg-gray-100">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={food.image}
                            alt={food.name}
                            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                            onError={(e) => {
                              (e.currentTarget as HTMLImageElement).src = 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400'
                            }}
                          />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <h4 className="font-bold text-sm text-gray-800 truncate group-hover:text-orange-600">
                          {food.name}
                        </h4>
                        {food.rating && (
                          <div className="flex items-center gap-1 mt-0.5">
                            <span className="text-yellow-500 text-[10px]">⭐</span>
                            <span className="text-[11px] font-medium text-gray-700">{food.rating}/5</span>
                          </div>
                        )}
                        {food.address && (
                          <p className="text-[11px] text-gray-500 mt-0.5 line-clamp-1">
                            📍 {food.address}
                          </p>
                        )}
                        {food.cost && (
                          <p className="text-xs font-semibold text-orange-600 mt-1">
                            {food.cost}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                );
              }
            })}
            {/* Action buttons */}
            {renderActionButtons(ui_data.actions)}
          </motion.div>
        );
      }

      // 5. Comprehensive (Multi-section)
      case "comprehensive": {
        return (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-3 space-y-3"
          >
            {ui_data.hotels && ui_data.hotels.length > 0 && (
              <div className="bg-blue-50/30 rounded-xl p-3 border border-blue-100">
                <h4 className="text-xs font-bold text-blue-800 mb-2 flex items-center gap-1">
                  🏨 Khách sạn ({ui_data.hotels.length})
                </h4>
                <div className="space-y-2">
                  {ui_data.hotels.slice(0, 3).map((hotel) => (
                    <div key={hotel.id} className="text-xs bg-white p-2 rounded-lg border border-blue-100">
                      <div className="font-semibold text-gray-800">{hotel.name}</div>
                      <div className="text-gray-600 mt-0.5">⭐ {hotel.rating}/5 • {hotel.priceRange || hotel.price_formatted || hotel.price_display || 'Liên hệ'}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {ui_data.spots && ui_data.spots.length > 0 && (
              <div className="bg-green-50/30 rounded-xl p-3 border border-green-100">
                <h4 className="text-xs font-bold text-green-800 mb-2 flex items-center gap-1">
                  📍 Địa điểm ({ui_data.spots.length})
                </h4>
                <div className="space-y-2">
                  {ui_data.spots.slice(0, 3).map((spot, idx) => (
                    <div key={spot.id || idx} className="text-xs bg-white p-2 rounded-lg border border-green-100">
                      <div className="font-semibold text-gray-800">{spot.name}</div>
                      {spot.rating && <div className="text-gray-600 mt-0.5">⭐ {spot.rating}/5</div>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {ui_data.food && ui_data.food.length > 0 && (
              <div className="bg-orange-50/30 rounded-xl p-3 border border-orange-100">
                <h4 className="text-xs font-bold text-orange-800 mb-2 flex items-center gap-1">
                  🍜 Ẩm thực ({ui_data.food.length})
                </h4>
                <div className="space-y-2">
                  {ui_data.food.slice(0, 2).map((food, idx) => (
                    <div key={food.id || idx} className="text-xs bg-white p-2 rounded-lg border border-orange-100">
                      {food.type === 'recommendation' ? (
                        <div>
                          <div className="font-semibold text-gray-800">🌟 {food.name}</div>
                          {food.dishes && <div className="text-gray-600 mt-0.5">{food.dishes.join(', ')}</div>}
                        </div>
                      ) : (
                        <div>
                          <div className="font-semibold text-gray-800">{food.name}</div>
                          {food.rating && <div className="text-gray-600 mt-0.5">⭐ {food.rating}/5</div>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        );
      }

      // 6. Itinerary Builder - Interactive mode for day-by-day selection
      case "itinerary_builder": {
        const spots = ui_data.spots || [];
        const currentDay = ui_data.current_day || 1;
        const totalDays = ui_data.total_days || 3;
        const selectedSet = selectedSpotsByDay[currentDay] || new Set<string>();

        const toggleSpotSelectionForDay = (spotId: string) => {
          setSelectedSpotsByDay(prev => {
            const next = { ...prev };
            const set = new Set(next[currentDay] || []);
            if (set.has(spotId)) set.delete(spotId); else set.add(spotId);
            next[currentDay] = set;
            return next;
          });
        };

        const handleSpotConfirmForDay = (spotsList: any[]) => {
          const selectedIndices = spotsList
            .map((spot, idx) => {
              const s = spot as Spot & { idx?: number };
              const spotIdx = s.idx || idx + 1;
              const spotId = s.id || String(spotIdx);
              return { spot, idx: spotIdx, spotId };
            })
            .filter(item => selectedSet.has(item.spotId))
            .map(item => item.idx);

          if (selectedIndices.length === 0) return;
          handleSend(selectedIndices.join(", "));
          setSelectedSpotsByDay(prev => ({ ...prev, [currentDay]: new Set<string>() }));
        };

        return (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-3"
          >
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
            <div className="grid grid-cols-1 gap-2 max-h-[280px] overflow-y-auto pr-1 scrollbar-thin mb-3">
              {spots.map((spot, idx) => {
                const s = spot as Spot & { idx?: number };
                const spotIdx = s.idx || idx + 1;
                const spotName = s.name || s.label || 'Unknown';
                const spotId = s.id || String(spotIdx);
                const isSelected = selectedSet.has(spotId);

                return (
                  <div
                    key={s.id || idx}
                    onClick={() => toggleSpotSelectionForDay(spotId)}
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
                    <div className="w-14 h-14 shrink-0 rounded-lg overflow-hidden bg-gray-100 relative">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={s.image || "https://placehold.co/100?text=No+Image"}
                        alt={spotName}
                        className="w-full h-full object-cover"
                        onError={(e) => (e.currentTarget as HTMLImageElement).src = "https://placehold.co/100?text=No+Image"}
                      />
                    </div>

                    {/* Spot info */}
                    <div className="flex-1 min-w-0 flex flex-col justify-center">
                      <h4 className="font-bold text-sm text-gray-800 truncate">
                        {spotName}
                      </h4>
                      {s.rating && (
                        <div className="flex items-center text-xs text-yellow-600 mt-0.5">
                          <Sparkles size={10} className="mr-1"/> {s.rating}/5
                        </div>
                      )}
                      {s.description && (
                        <p className="text-xs text-gray-500 line-clamp-1 mt-0.5">{s.description}</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Nút Xem thêm */}
            {ui_data.show_load_more_button && (
              <div className="px-0 py-2 border-t border-gray-200">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    // Send "xem thêm" message to backend
                    handleSend("xem thêm");
                  }}
                  className="w-full py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold rounded-lg transition-all text-sm flex items-center justify-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                  </svg>
                  {ui_data.load_more_text || "Xem thêm"}
                </button>
              </div>
            )}

            {/* Nút Xác nhận */}
            {selectedSet.size > 0 && (
              <div className="sticky bottom-0 pt-2 pb-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSpotConfirmForDay(spots);
                  }}
                  className="w-full py-2.5 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all flex items-center justify-center gap-2 text-sm"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Xác nhận ({selectedSet.size} địa điểm)
                </button>
              </div>
            )}
          </motion.div>
        );
      }

      // 7. Itinerary Display (auto-generated JSON from backend)
      case "itinerary_display": {
        const itinerary = ui_data.itinerary;
        if (!itinerary) return null;

        const days = itinerary.days || [];
        console.log("[DEBUG itinerary_display] days=", days, "itinerary=", itinerary);
        const budgetWarning = itinerary.budget_warning;
        const budgetBreakdown = itinerary.budget_breakdown;
        const summaryLines: string[] = [];
        if (itinerary.duration) summaryLines.push(`${itinerary.duration} ngày`);
        if (itinerary.people_count) summaryLines.push(`${itinerary.people_count} người`);
        if (itinerary.start_date) summaryLines.push(`Bắt đầu: ${itinerary.start_date}`);

        const formatMoney = (v?: number) => {
          if (!v && v !== 0) return undefined;
          try {
            return v.toLocaleString("vi-VN") + " VND";
          } catch (_e) {
            return `${v} VND`;
          }
        };

        return (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-3 bg-white rounded-xl border border-amber-100 overflow-hidden shadow-xs">
            <div className="bg-amber-50/60 p-3 border-b border-amber-100 flex flex-wrap items-center gap-2">
              <Sparkles size={14} className="text-amber-600" />
              <span className="text-xs font-bold text-amber-800">
                🎉 Lịch trình tự động: {itinerary.location || "Chuyến đi"}
              </span>
              {summaryLines.length > 0 && (
                <span className="text-[11px] text-amber-700">({summaryLines.join(" • ")})</span>
              )}
            </div>

            <div className="p-3 space-y-3">
              {/* Cost + Budget */}
              {(itinerary.estimated_cost || itinerary.budget) && (
                <div className="flex flex-wrap gap-2 text-[11px] text-gray-700">
                  {itinerary.estimated_cost && (
                    <span className="px-2 py-1 bg-green-50 border border-green-100 rounded-full text-green-700 font-semibold">
                      Ước tính: {formatMoney(itinerary.estimated_cost)}
                    </span>
                  )}
                  {itinerary.budget && (
                    <span className="px-2 py-1 bg-blue-50 border border-blue-100 rounded-full text-blue-700 font-semibold">
                      Ngân sách: {formatMoney(itinerary.budget)}
                    </span>
                  )}
                </div>
              )}

              {/* Budget warning */}
              {budgetWarning && (
                <div className="bg-red-50 border border-red-100 rounded-lg p-2 text-[12px] text-red-700 space-y-1">
                  <div className="font-semibold flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
                      <path d="M12 9v4" />
                      <path d="M12 17h.01" />
                    </svg>
                    <span>{budgetWarning.message}</span>
                  </div>
                  {budgetWarning.suggestions && budgetWarning.suggestions.length > 0 && (
                    <ul className="list-disc list-inside text-[11px] text-red-700 space-y-0.5">
                      {budgetWarning.suggestions.map((s: string, idx: number) => (
                        <li key={idx}>{s}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {/* Budget breakdown */}
              {budgetBreakdown && (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px] text-gray-700">
                  <div className="px-2 py-1 bg-white border border-gray-100 rounded-lg">
                    <div className="text-[10px] text-gray-500">Khách sạn/đêm</div>
                    <div className="font-semibold text-gray-800">{formatMoney(budgetBreakdown.accommodation_per_night)}</div>
                  </div>
                  <div className="px-2 py-1 bg-white border border-gray-100 rounded-lg">
                    <div className="text-[10px] text-gray-500">Số đêm</div>
                    <div className="font-semibold text-gray-800">{budgetBreakdown.nights}</div>
                  </div>
                  <div className="px-2 py-1 bg-white border border-gray-100 rounded-lg">
                    <div className="text-[10px] text-gray-500">Ăn uống</div>
                    <div className="font-semibold text-gray-800">{formatMoney(budgetBreakdown.food)}</div>
                  </div>
                  <div className="px-2 py-1 bg-white border border-gray-100 rounded-lg">
                    <div className="text-[10px] text-gray-500">Di chuyển</div>
                    <div className="font-semibold text-gray-800">{formatMoney(budgetBreakdown.transport)}</div>
                  </div>
                  <div className="px-2 py-1 bg-white border border-gray-100 rounded-lg">
                    <div className="text-[10px] text-gray-500">Hoạt động</div>
                    <div className="font-semibold text-gray-800">{formatMoney(budgetBreakdown.activities)}</div>
                  </div>
                  <div className="px-2 py-1 bg-white border border-gray-100 rounded-lg col-span-2 sm:col-span-1">
                    <div className="text-[10px] text-gray-500">Tổng</div>
                    <div className="font-semibold text-gray-800">{formatMoney(budgetBreakdown.total)}</div>
                  </div>
                </div>
              )}

              {itinerary.reasoning && (
                <div className="text-[12px] text-gray-700 bg-gray-50 border border-gray-100 rounded-lg p-2">
                  {itinerary.reasoning}
                </div>
              )}

              {/* Hotels - Clickable for selection */}
              {itinerary.hotels && itinerary.hotels.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs font-bold text-blue-800 flex items-center gap-2">
                    🏨 Khách sạn gợi ý ({itinerary.hotels.length})
                    <span className="text-[10px] text-blue-600 font-normal">- Click để chọn</span>
                  </div>
                  <div className="grid grid-cols-1 gap-2">
                    {itinerary.hotels.map((hotel, idx) => (
                      <div
                        key={hotel.id || idx}
                        onClick={() => {
                          const hotelName = hotel.name || "Khách sạn";
                          handleSend(`Tôi chọn khách sạn: ${hotelName}`);
                        }}
                        className="flex gap-3 p-2 bg-white rounded-lg border border-blue-100 shadow-[0_1px_3px_rgba(0,0,0,0.04)] cursor-pointer hover:border-blue-400 hover:bg-blue-50/50 transition-all group"
                      >
                        <div className="w-14 h-14 rounded-md bg-gray-100 overflow-hidden">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={hotel.image || "https://placehold.co/100?text=Hotel"}
                            alt={hotel.name || "Khách sạn"}
                            className="w-full h-full object-cover"
                            onError={(e) => (e.currentTarget as HTMLImageElement).src = "https://placehold.co/100?text=Hotel"}
                          />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-semibold text-gray-800 truncate group-hover:text-blue-700">{hotel.name || "Khách sạn"}</div>
                          <div className="text-[11px] text-gray-600 flex gap-2 flex-wrap mt-0.5">
                            {hotel.rating && <span className="px-2 py-0.5 bg-yellow-50 text-yellow-700 rounded-full border border-yellow-100">⭐ {hotel.rating}/5</span>}
                            {hotel.price && <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded-full border border-emerald-200 font-medium">
                              💵 {typeof hotel.price === 'number' ? hotel.price.toLocaleString('vi-VN') : hotel.price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')} ₫
                            </span>}
                            {hotel.address && <span className="text-[11px] text-gray-500 block truncate">{hotel.address}</span>}
                          </div>
                        </div>
                        {/* Selection indicator */}
                        <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                          <span className="text-[10px] text-blue-600 font-semibold whitespace-nowrap">Chọn →</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Days */}
              <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1 scrollbar-thin">
                {days.map((day) => (
                  <div key={day.day} className="border border-amber-100 rounded-lg p-2 bg-amber-50/40">
                    <div className="text-xs font-bold text-amber-800 mb-2 flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-amber-100 text-amber-800 flex items-center justify-center text-xs font-bold">{day.day}</span>
                      <span>Ngày {day.day}</span>
                    </div>
                    <div className="grid grid-cols-1 gap-2">
                      {(day.spots || []).map((spot, idx) => (
                        <div
                          key={spot.id || idx}
                          className="flex gap-3 p-2 bg-white rounded-lg border border-amber-100 shadow-[0_1px_3px_rgba(0,0,0,0.04)]"
                        >
                          <div className="w-12 h-12 rounded-md bg-gray-100 overflow-hidden">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                              src={spot.image || "https://placehold.co/80?text=Spot"}
                              alt={spot.name || "Địa điểm"}
                              className="w-full h-full object-cover"
                              onError={(e) => (e.currentTarget as HTMLImageElement).src = "https://placehold.co/80?text=Spot"}
                            />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-semibold text-gray-800 truncate">{spot.name || "Địa điểm đề xuất"}</div>
                            <div className="text-[11px] text-gray-600 flex gap-2 flex-wrap mt-0.5">
                              {spot.session && <span className="px-2 py-0.5 bg-amber-50 text-amber-700 rounded-full border border-amber-100">{spot.session}</span>}
                              {spot.category && <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full border border-blue-100">{spot.category}</span>}
                              {spot.rating && <span className="px-2 py-0.5 bg-green-50 text-green-700 rounded-full border border-green-100">⭐ {spot.rating}/5</span>}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        );
      }

      // 8. Itinerary - Final generated itinerary
      case "itinerary": {
        const items = ui_data.items || [];
        return (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-3 bg-white rounded-xl border border-green-100 overflow-hidden shadow-xs">
            <div className="bg-green-50/50 p-2 border-b border-green-100 flex items-center gap-2">
               <MapPin size={14} className="text-green-600"/>
               <span className="text-xs font-bold text-green-800">✅ Lịch trình hoàn thành: {ui_data.destination} ({ui_data.days || ui_data.total_days} ngày)</span>
            </div>
            <div className="max-h-[300px] overflow-y-auto p-2 space-y-3 scrollbar-thin">
              {items.map((item) => (
                <div key={item.day} className="relative pl-3 border-l-2 border-green-200">
                  <div className="absolute -left-[5px] top-0 w-2 h-2 rounded-full bg-green-400"></div>
                  <div className="text-xs font-bold text-gray-800 mb-1">Ngày {item.day}: {item.title}</div>
                  <div className="space-y-1">
                    {item.morning && <div className="text-[11px] text-gray-600"><span className="font-semibold text-green-600">Sáng:</span> {item.morning}</div>}
                    {item.afternoon && <div className="text-[11px] text-gray-600"><span className="font-semibold text-orange-600">Chiều:</span> {item.afternoon}</div>}
                    {item.evening && <div className="text-[11px] text-gray-600"><span className="font-semibold text-purple-600">Tối:</span> {item.evening}</div>}
                  </div>
                </div>
              ))}
            </div>
            {/* CRITICAL FIX: Add action buttons for next steps */}
            {renderActionButtons(ui_data.actions)}
          </motion.div>
        );
      }

      // 8. Tips - Location tips with categories
      case "tips": {
        const categories = ui_data.tips_categories || [];
        return (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-3 bg-white rounded-xl border border-blue-100 overflow-hidden shadow-xs">
            <div className="bg-blue-50/50 p-2 border-b border-blue-100 flex items-center gap-2">
               <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-600"><circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4"></path><path d="M12 8h.01"></path></svg>
               <span className="text-xs font-bold text-blue-800">💡 Lưu ý cho chuyến đi</span>
            </div>
            <div className="max-h-[280px] overflow-y-auto p-2 space-y-2 scrollbar-thin">
              {categories.map((cat, idx) => (
                <div key={idx} className="flex gap-2 items-start bg-gray-50/50 rounded-lg p-2">
                  <span className="text-base">{cat.icon}</span>
                  <div className="flex-1">
                    <div className="text-[11px] font-bold text-gray-800 mb-0.5">{cat.title}</div>
                    <div className="text-[10px] text-gray-600">{cat.content}</div>
                  </div>
                </div>
              ))}
            </div>
            {/* CRITICAL: Action buttons */}
            {renderActionButtons(ui_data.actions)}
          </motion.div>
        );
      }

      // 9. Spot Selector Table - Multi-choice với checkbox
      case "spot_selector_table": {
        const rows = ui_data.rows || [];
        const defaultSelectedIds = ui_data.default_selected_ids || [];
        const destination = ui_data.destination || "";
        const duration = ui_data.days || ui_data.total_days || ui_data.duration || 1;

        const handleSpotSubmit = (selectedIds: string[]) => {
          handleSend(JSON.stringify({ action: "submit", selected_spot_ids: selectedIds }));
        };

        const handleSpotCancel = () => {
          handleSend(JSON.stringify({ action: "cancel" }));
        };

        const handleSpotSkip = () => {
          handleSend(JSON.stringify({ action: "skip" }));
        };

        return (
          <SpotSelectorTable
            rows={rows}
            defaultSelectedIds={defaultSelectedIds}
            destination={destination}
            duration={duration}
            onSubmit={handleSpotSubmit}
            onCancel={handleSpotCancel}
            onSkip={handleSpotSkip}
          />
        );
      }

      // 10. Distance Info - Khoảng cách từ khách sạn đến các địa điểm
      case "distance_info": {
        const hotelName = ui_data.hotel || "Khách sạn";
        const distances = ui_data.distances || [];

        return (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-3 bg-white rounded-xl border border-blue-100 overflow-hidden shadow-xs">
            <div className="bg-blue-50/50 p-2 border-b border-blue-100 flex items-center gap-2">
              <MapPin size={14} className="text-blue-600"/>
              <span className="text-xs font-bold text-blue-800">📏 Khoảng cách từ {hotelName}</span>
            </div>
            <div className="max-h-[320px] overflow-y-auto p-3 scrollbar-thin">
              {distances.length > 0 ? (
                <div className="space-y-2">
                  {distances.map((dist, idx) => {
                    const timeMinutes = Math.round((dist.distance_km / 30) * 60);
                    const timeStr = timeMinutes < 60
                      ? `${timeMinutes} phút`
                      : `${Math.floor(timeMinutes / 60)}h${timeMinutes % 60}m`;

                    return (
                      <div key={idx} className="flex items-start gap-3 p-3 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-all">
                        {/* Ảnh spot */}
                        <div className="w-16 h-16 shrink-0 rounded-lg overflow-hidden bg-gray-100">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={dist.image || 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=200'}
                            alt={dist.name}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              (e.currentTarget as HTMLImageElement).src = 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=200'
                            }}
                          />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-semibold text-gray-800 truncate">{dist.name}</div>

                          <div className="flex items-center gap-3 mt-1">
                            <span className="text-xs font-bold text-blue-600">
                              📍 {dist.distance_km} km
                            </span>
                            <span className="text-xs text-gray-500">
                              🕐 ~{timeStr}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center text-gray-500 text-sm py-4">
                  Không có thông tin khoảng cách
                </div>
              )}
              <div className="mt-3 pt-2 border-t border-gray-200">
                <p className="text-xs text-gray-500 text-center">
                  💡 Thời gian ước tính với tốc độ 30 km/h
                </p>
              </div>
            </div>
          </motion.div>
        );
      }

      default: return null;
      }
    } catch (err) {
      logger.warn(`[renderGenUI] Error rendering ui_type=${msg.ui_type}: ${err}`);
      return (
        <div className="mt-3 p-2 bg-red-50 border border-red-100 rounded-lg text-[11px] text-red-700">
          ⚠️ Lỗi hiển thị: {String(err)}
        </div>
      );
    }
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 font-sans flex flex-col items-end pointer-events-none">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className={`pointer-events-auto bg-white border border-gray-200 flex flex-col overflow-hidden ${
              isFullscreen
                ? "w-screen h-screen fixed inset-0 rounded-none shadow-none mb-0"
                : "w-[360px] h-[550px] rounded-2xl shadow-2xl mb-4"
            }`}
          >
            {/* HEADER */}
            <div className="bg-white p-3 border-b border-gray-100 flex justify-between items-center shadow-xs z-10">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-linear-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-sm">
                  <Bot size={16} />
                </div>
                <div>
                  <h3 className="font-bold text-sm text-gray-800">SaoLa AI</h3>
                  <div className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"/>
                    <span className="text-[10px] text-gray-500 font-medium">Sẵn sàng hỗ trợ</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-1">
                 <button onClick={handleNewConversation} className="p-1.5 hover:bg-gray-100 rounded-md text-gray-400 hover:text-gray-600 transition" title="Cuộc trò chuyện mới">
                    <RefreshCw size={14}/>
                 </button>
                 <button onClick={() => setIsFullscreen(!isFullscreen)} className="p-1.5 hover:bg-gray-100 rounded-md text-gray-400 hover:text-gray-600 transition" title={isFullscreen ? "Thu nhỏ" : "Phóng to"}>
                    {isFullscreen ? <Minimize2 size={14}/> : <Maximize2 size={14}/>}
                 </button>
                 <button onClick={() => setIsOpen(false)} className="p-1.5 hover:bg-gray-100 rounded-md text-gray-400 hover:text-gray-600 transition">
                    <X size={16} />
                 </button>
              </div>
            </div>

            {/* MESSAGES AREA */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/50 scrollbar-thin">
              {messages.map((rawMsg, idx) => {
                // Normalize content to a safe string for rendering
                const contentStr = (() => {
                  if (typeof rawMsg.content === "string") return rawMsg.content;
                  // For non-string content, only stringify if safe
                  if (rawMsg.content === null || rawMsg.content === undefined) return "";
                  if (typeof rawMsg.content === "object" && !Array.isArray(rawMsg.content)) {
                    // If it's a plain object with minimal fields, stringify it
                    try {
                      const str = JSON.stringify(rawMsg.content);
                      if (str.length > 500) return "[Object]"; // Too long, skip
                      return str;
                    } catch (_e) {
                      return "[Object]";
                    }
                  }
                  if (Array.isArray(rawMsg.content)) {
                    // Arrays of objects - likely UI data, don't stringify
                    return "[Array of items]";
                  }
                  return String(rawMsg.content);
                })();

                const msg: Message = { ...rawMsg, content: contentStr } as Message;

                return (
                  <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[85%] ${msg.role === "user" ? "bg-blue-600 text-white rounded-2xl rounded-tr-sm" : "bg-white border border-gray-200 rounded-2xl rounded-tl-sm shadow-sm"} p-3`}>
                      {/* Hide raw text when we render a full itinerary card to avoid duplicate content */}
                      {!(msg.role === "assistant" && msg.ui_type === "itinerary_display") && contentStr && (
                        <div className={`text-sm prose prose-sm max-w-none ${msg.role === "user" ? "prose-invert" : ""}`}>
                          <ReactMarkdown
                            components={{
                              a: ({...props}) => <a target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 underline" {...props} />
                            }}
                          >{msg.content}</ReactMarkdown>
                        </div>
                      )}
                      {/* Render UI kèm theo tin nhắn */}
                      {msg.role === "assistant" && renderGenUI(msg)}
                    </div>
                  </div>
                );
              })}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-100 rounded-full py-2 px-4 shadow-sm flex items-center gap-2">
                    <Loader2 className="w-3 h-3 animate-spin text-blue-500"/>
                    <span className="text-xs text-gray-400">Đang soạn tin...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* INPUT AREA */}
            <div className="p-3 bg-white border-t border-gray-100">
              <form
                onSubmit={(e) => { e.preventDefault(); handleSend(); }}
                className="flex items-center gap-2 bg-gray-50 p-1.5 rounded-xl border border-gray-200 focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-50 transition-all"
              >
                <Input
                  id="chat-input"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Nhập yêu cầu của bạn..."
                  className="flex-1 border-none bg-transparent shadow-none focus-visible:ring-0 text-sm px-2 h-9"
                  disabled={isLoading}
                />
                <Button
                  type="submit"
                  size="icon"
                  className={`h-8 w-8 rounded-lg transition-all ${input.trim() ? 'bg-blue-600 hover:bg-blue-700 shadow-md' : 'bg-gray-300'}`}
                  disabled={!input.trim() || isLoading}
                >
                  <Send size={14} className="ml-0.5" />
                </Button>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* TOGGLE BUTTON */}
      {!isOpen && (
        <motion.button
          initial={{ scale: 0 }} animate={{ scale: 1 }}
          whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}
          onClick={() => setIsOpen(true)}
          className="pointer-events-auto bg-blue-600 hover:bg-blue-700 text-white p-3.5 rounded-full shadow-lg shadow-blue-600/30 transition-all flex items-center justify-center"
        >
          <MessageCircle size={24} />
        </motion.button>
      )}
    </div>
  )
}

export default ChatWidget
