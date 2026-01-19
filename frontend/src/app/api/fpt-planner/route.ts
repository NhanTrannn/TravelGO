export const runtime = "nodejs";
import csvDB from "@/lib/csvdb";
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { messages, companions, interests, conversation_stage, plan_shown, hotels_shown } = body;
    let { destination, budget, days, selected_hotel } = body;

    console.log("🎯 Conversation State:", {
      stage: conversation_stage,
      plan_shown,
      hotels_shown,
      destination,
      days
    });

    // PARSE CONTEXT TỪ USER MESSAGES NẾU CHƯA CÓ
    if (!destination || !days) {
      const lastUserMsg = messages.filter((m: { role: string }) => m.role === "user").pop();
      if (lastUserMsg) {
        const text = lastUserMsg.content.toLowerCase();

        // Extract destination (tìm tên thành phố Việt Nam)
        const vnCities = ["đà lạt", "nha trang", "hội an", "phú quốc", "đà nẵng", "hạ long", "sapa", "hồ chí minh", "hà nội", "huế", "mũi né", "vũng tàu"];
        for (const city of vnCities) {
          if (text.includes(city)) {
            destination = city.split(" ").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
            break;
          }
        }

        // Extract days
        if (text.match(/(\d+)\s*(ngày|day)/)) {
          const match = text.match(/(\d+)\s*(ngày|day)/);
          if (match) days = `${match[1]} ngày`;
        } else if (text.includes("2 ngày 1 đêm") || text.includes("2n1đ")) {
          days = "2 ngày 1 đêm";
        } else if (text.includes("3 ngày 2 đêm") || text.includes("3n2đ")) {
          days = "3 ngày 2 đêm";
        }

        // Extract budget
        if (text.includes("tiết kiệm")) budget = "💰 Tiết kiệm (<5tr)";
        else if (text.includes("trung bình")) budget = "💵 Trung bình (5-10tr)";
        else if (text.includes("sang")) budget = "💎 Sang trọng (>10tr)";
      }
    }

    // KIỂM TRA XEM USER CÓ CHỌN KHÁCH SẠN KHÔNG
    const lastUserMsg = messages.filter((m: { role: string }) => m.role === "user").pop();
    if (lastUserMsg && lastUserMsg.content.toLowerCase().includes("chọn khách sạn:")) {
      // Extract hotel name: "Chọn khách sạn: Luxury Place Hotel" → "Luxury Place Hotel"
      const hotelMatch = lastUserMsg.content.match(/chọn khách sạn:\s*(.+)/i);
      if (hotelMatch) {
        selected_hotel = hotelMatch[1].trim();
        console.log("🏨 User selected hotel:", selected_hotel);

        // Return response with next action options
        return NextResponse.json({
          reply: `Tuyệt vời! Bạn đã chọn **${selected_hotel}**. 🎉\n\nBạn muốn tôi giúp gì tiếp theo?`,
          ui_type: "options",
          ui_data: {
            options: [
              "📊 Tính chi phí chuyến đi này",
              "🗺️ Lập lịch trình chi tiết",
              "🔍 Xem thêm khách sạn khác"
            ]
          },
          intent: "collect_info",
          context: {
            destination: destination || "",
            budget: budget || "",
            days: days || "",
            companions: companions || "",
            interests: interests || "",
            selected_hotel: selected_hotel
          }
        });
      }
    }

    console.log("🎯 Planner Request:", { destination, budget, days, companions, interests });

    // 1. GỌI FPT SERVICE ĐỂ PHÂN TÍCH Ý ĐỊNH + GỬI KÈM CONTEXT
    const fptRes = await fetch("http://127.0.0.1:8001/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages,
        context: {
          conversation_stage: conversation_stage || "initial",
          plan_shown: plan_shown || false,
          hotels_shown: hotels_shown || false,
          destination: destination || "",
          days: days || "",
          budget: budget || ""
        }
      })
    });

    const fptData = await fptRes.json();

    // CẬP NHẬT CONTEXT TỪ FPT RESPONSE (extracted_info)
    if (fptData.extracted_info) {
      if (fptData.extracted_info.destination) destination = fptData.extracted_info.destination;
      if (fptData.extracted_info.days) days = fptData.extracted_info.days;
      if (fptData.extracted_info.budget) budget = fptData.extracted_info.budget;
    }

    console.log("📊 Context after FPT:", { destination, days, budget });

    // 2. CHECK INTENT TỪ FPT RESPONSE
    const intent = fptData.intent || "collect_info";
    console.log("🎯 Detected Intent:", intent);

    // 3. XỬ LÝ THEO INTENT VỚI CONVERSATION CONTEXT

    // 3A. INTENT = "info" → Thử tìm trong DB trước, nếu không có mới dùng simple-chat
    if (intent === "info") {
      console.log(`💬 Intent=info - Checking database first for real data`);

      // Extract location từ message để query DB
      const lastUserMsg = messages.filter((m: { role: string }) => m.role === "user").pop();
      let searchLocation = destination || "";

      // Nếu chưa có destination, thử extract từ message
      if (!searchLocation && lastUserMsg) {
        const text = lastUserMsg.content.toLowerCase();
        const vnCities = ["đà lạt", "nha trang", "hội an", "phú quốc", "đà nẵng", "hạ long", "sapa", "hồ chí minh", "hà nội", "huế", "mũi né", "vũng tàu", "cầu rồng", "cầu vàng"];
        for (const city of vnCities) {
          if (text.includes(city)) {
            searchLocation = city.split(" ").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
            break;
          }
        }
      }

      // Normalize location
      const cityKeywords = ["Hà Nội", "Đà Lạt", "Nha Trang", "Đà Nẵng", "Hội An", "Phú Quốc", "Vũng Tàu", "Huế", "Sài Gòn", "Hồ Chí Minh", "Hạ Long", "Sapa"];
      let normalizedCity = searchLocation;
      for (const city of cityKeywords) {
        if (searchLocation.includes(city)) {
          normalizedCity = city;
          break;
        }
      }

      // Query database nếu có location
      let dbResults = null;
      if (normalizedCity) {
        console.log(`📍 Querying database for: ${normalizedCity}`);
        try {
          // Sử dụng csvDB thay vì prisma
          let listings = csvDB.listing.searchByLocation(normalizedCity);

          // Sắp xếp theo giá và giới hạn 5 kết quả
          listings = listings
            .sort((a, b) => a.price - b.price)
            .slice(0, 5);

          if (listings.length > 0) {
            dbResults = listings;
            console.log(`✅ Found ${listings.length} listings in database`);
          } else {
            console.log(`⚠️ No listings found for "${normalizedCity}" in database`);
          }
        } catch (dbError) {
          console.error("❌ Database query error:", dbError);
        }
      }

      // Nếu CÓ data từ DB → Trả về thông tin thực tế
      if (dbResults && dbResults.length > 0) {
        console.log(`📊 Using real data from database`);

        // Tạo reply từ data thực tế
        const listingSummary = dbResults.map((l, idx) =>
          `${idx + 1}. **${l.title}** - ${l.location} (${(l.price / 1000).toFixed(0)}k/đêm)`
        ).join("\n");

        const reply = `Dựa trên dữ liệu thực tế, đây là thông tin về ${normalizedCity}:\n\n${listingSummary}\n\n💡 Bạn muốn biết thêm chi tiết nào?`;

        return NextResponse.json({
          reply,
          ui_type: "none",
          intent,
          data_source: "database", // Đánh dấu dùng DB
          listings_count: dbResults.length,
          context: {
            destination: normalizedCity || destination || "",
            budget: budget || "",
            days: days || "",
            companions: companions || "",
            interests: interests || "",
            conversation_stage: conversation_stage || "initial",
            plan_shown: plan_shown || false,
            hotels_shown: hotels_shown || false
          }
        });
      }

      // Nếu KHÔNG CÓ data trong DB → Chuyển sang simple-chat
      console.log(`🤖 No data in DB, redirecting to simple-chat for AI knowledge`);

      try {
        const simpleChatRes = await fetch("http://127.0.0.1:8001/simple-chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: messages.slice(-10),
            temperature: 0.7,
            max_tokens: 512
          })
        });

        const simpleChatData = await simpleChatRes.json();

        console.log(`✅ Simple-chat response received (${simpleChatData.latency_seconds}s)`);

        return NextResponse.json({
          reply: simpleChatData.reply + "\n\n⚠️ *Thông tin này dựa trên kiến thức AI, có thể không hoàn toàn chính xác.*",
          ui_type: "none",
          intent,
          data_source: "ai_knowledge", // Đánh dấu dùng AI
          latency_seconds: simpleChatData.latency_seconds,
          tokens_used: simpleChatData.tokens_used,
          context: {
            destination: destination || "",
            budget: budget || "",
            days: days || "",
            companions: companions || "",
            interests: interests || "",
            conversation_stage: conversation_stage || "initial",
            plan_shown: plan_shown || false,
            hotels_shown: hotels_shown || false
          }
        });
      } catch (error) {
        console.error("❌ Simple-chat error, fallback to original reply:", error);
        return NextResponse.json({
          reply: fptData.reply + "\n\n⚠️ *Thông tin tổng quát, có thể không chính xác.*",
          ui_type: "none",
          intent,
          data_source: "fallback",
          context: {
            destination: destination || "",
            budget: budget || "",
            days: days || "",
            companions: companions || "",
            interests: interests || "",
            conversation_stage: conversation_stage || "initial",
            plan_shown: plan_shown || false,
            hotels_shown: hotels_shown || false
          }
        });
      }
    }

    // 3C. INTENT = "budget" → Luôn show breakdown
    if (intent === "budget") {
      console.log(`💬 Intent=budget - Returning budget breakdown`);

      let ui_data: Record<string, unknown> | undefined = undefined;
      if (fptData.budget_breakdown) {
        ui_data = { budget: fptData.budget_breakdown };
      }

      return NextResponse.json({
        reply: fptData.reply,
        ui_type: "none",
        ui_data,
        intent,
        latency_seconds: fptData.latency_seconds,
        tokens_used: fptData.tokens_used,
        context: {
          destination: destination || "",
          budget: budget || "",
          days: days || "",
          companions: companions || "",
          interests: interests || "",
          conversation_stage: conversation_stage || "initial",
          plan_shown: plan_shown || false,
          hotels_shown: hotels_shown || false
        }
      });
    }

    // 3D. INTENT = "itinerary" → Luôn show plan UI (cho phép tạo nhiều plan khác nhau)
    if (intent === "itinerary") {
      console.log(`💬 Intent=itinerary - Generating new plan (plan_shown=${plan_shown})`);

      // Luôn show plan UI, không giới hạn số lần
      console.log("📋 Generating itinerary plan with UI");
      let ui_type: string = "none";
      let ui_data: Record<string, unknown> | undefined = undefined;

      if (fptData.itinerary_plan && Array.isArray(fptData.itinerary_plan.itinerary)) {
        ui_type = "itinerary_plan";
        ui_data = {
          days: fptData.itinerary_plan.days,
          destination: fptData.itinerary_plan.destination,
          items: fptData.itinerary_plan.itinerary.map((d: { day: number; title: string; morning: string; afternoon: string; evening: string; notes: string }) => ({
            day: d.day,
            title: d.title,
            morning: d.morning,
            afternoon: d.afternoon,
            evening: d.evening,
            notes: d.notes
          }))
        };
      }

      return NextResponse.json({
        reply: fptData.reply,
        ui_type,
        ui_data,
        intent,
        latency_seconds: fptData.latency_seconds,
        tokens_used: fptData.tokens_used,
        context: {
          destination: destination || "",
          budget: budget || "",
          days: days || "",
          companions: companions || "",
          interests: interests || "",
          conversation_stage: "plan_shown",
          plan_shown: true,
          hotels_shown: hotels_shown || false
        }
      });
    }

    // 3E. INTENT = "filter" → Xử lý lọc địa danh, KHÔNG show plan
    if (intent === "filter") {
      console.log(`💬 Intent=filter - Filtering places/attractions`);
      return NextResponse.json({
        reply: fptData.reply,
        ui_type: "none",
        intent,
        latency_seconds: fptData.latency_seconds,
        tokens_used: fptData.tokens_used,
        context: {
          destination: destination || "",
          budget: budget || "",
          days: days || "",
          companions: companions || "",
          interests: interests || "",
          conversation_stage: conversation_stage || "initial",
          plan_shown: plan_shown || false,
          hotels_shown: hotels_shown || false
        }
      });
    }

    // 3F. CHECK XEM ĐÃ SHOW HOTELS CHƯA (cho intent="search" hoặc "collect_info")
    // Ưu tiên dùng context thay vì scan messages
    console.log("🔍 Hotel status:", { hotels_shown, destination, days });

    // 3G. NẾU INTENT="search" + ĐỦ INFO + CHƯA SHOW HOTELS → QUERY DATABASE
    if (intent === "search" && destination && days && !hotels_shown) {
      console.log("🏨 Intent=search - Querying database for:", destination);

      // Normalize destination: "Đống Đa Hà Nội" → "Hà Nội", "Quận 1 Sài Gòn" → "Sài Gòn"
      const cityKeywords = ["Hà Nội", "Đà Lạt", "Nha Trang", "Đà Nẵng", "Hội An", "Phú Quốc", "Vũng Tàu", "Huế", "Sài Gòn", "Hồ Chí Minh", "Hạ Long", "Sapa"];
      let normalizedCity = destination;
      for (const city of cityKeywords) {
        if (destination.includes(city)) {
          normalizedCity = city;
          break;
        }
      }
      console.log("📍 Normalized destination:", destination, "→", normalizedCity);

      // Query ALL hotels từ CSV database (không giới hạn)
      const hotels = csvDB.listing.searchByLocation(normalizedCity);

      // Sắp xếp theo giá tăng dần
      hotels.sort((a, b) => a.price - b.price);

      console.log(`✅ Found ${hotels.length} hotels for "${normalizedCity}" in CSV`);

      // 3. NẾU CÓ HOTELS → TRẢ VỀ DẠNG GENERATIVE UI
      if (hotels.length > 0) {
        console.log("🏨 Returning hotel cards UI");
        return NextResponse.json({
          reply: `Tuyệt vời! Tôi tìm thấy ${hotels.length} khách sạn phù hợp với bạn tại ${normalizedCity}. Hãy chọn nơi bạn thích nhé! 🏨`,
          ui_type: "hotel_cards",
          ui_data: {
            hotels: hotels.map(h => ({
              id: h.id,
              name: h.title,
              address: h.location,
              priceRange: `${(h.price / 1000).toFixed(0)}k/đêm`,
              rating: h.rating || 4.5,
              image: h.imageSrc,
              description: h.description.substring(0, 150) + "..."
            }))
          },
          context: {
            destination,
            budget,
            days,
            companions,
            interests,
            conversation_stage: "exploring_hotels",
            plan_shown: plan_shown || false,
            hotels_shown: true
          }
        });
      } else {
        console.log("⚠️ No hotels found in database for:", normalizedCity, "(original:", destination, ")");
        // Fallback: trả về message hướng dẫn thử lại với tên thành phố chính
        return NextResponse.json({
          reply: `Xin lỗi, tôi chưa tìm thấy khách sạn nào tại "${destination}". Bạn có thể thử lại với tên thành phố chính như: Hà Nội, Đà Lạt, Nha Trang, Đà Nẵng, Phú Quốc... 🏨`,
          ui_type: "none",
          context: {
            destination: "",  // Reset destination để user nhập lại
            budget,
            days,
            companions,
            interests,
            conversation_stage: "initial",
            plan_shown: plan_shown || false,
            hotels_shown: false
          }
        });
      }
    } else if (hotels_shown && intent === "search") {
      console.log("💬 Hotels already shown + intent=search, letting FPT answer");
    } else if (intent === "collect_info") {
      console.log("⏳ Intent=collect_info - Not enough info yet. destination:", destination, "days:", days);
    }

    // 4. DEFAULT: TRẢ VỀ RESPONSE TỪ FPT (collect_info với GenUI buttons)
    console.log("📤 Returning FPT response (intent:", intent, ")");
    return NextResponse.json({
      reply: fptData.reply,
      intent: intent,
      ui_type: fptData.ui_type,
      ui_data: fptData.ui_data,
      latency_seconds: fptData.latency_seconds,
      tokens_used: fptData.tokens_used,
      context: {
        destination: destination || "",
        budget: budget || "",
        days: days || "",
        companions: companions || "",
        interests: interests || "",
        conversation_stage: conversation_stage || "initial",
        plan_shown: plan_shown || false,
        hotels_shown: hotels_shown || false
      }
    });

  } catch (error) {
    console.error("❌ Planner Error:", error);
    return NextResponse.json({
      reply: "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau.",
      ui_type: "none",
      error: error instanceof Error ? error.message : "Unknown error"
    }, { status: 500 });
  }
}
