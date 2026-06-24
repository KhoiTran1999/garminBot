export default {
    async fetch(request, env, ctx) {
        if (request.method !== "POST") {
            return new Response("Method not allowed", { status: 405 });
        }

        try {
            const update = await request.json();
            
            let chatId = "";
            let text = "";

            // Xử lý Callback Query (Nút bấm Inline)
            if (update.callback_query) {
                chatId = String(update.callback_query.message.chat.id);
                text = update.callback_query.data;
                
                // Trả lời callback query ngay lập tức để nút không bị trạng thái loading
                const answerUrl = `https://api.telegram.org/bot${env.TG_BOT_TOKEN}/answerCallbackQuery`;
                fetch(answerUrl, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ callback_query_id: update.callback_query.id })
                }).catch(e => console.log("Answer callback error:", e));

            // Xử lý Text Message thường
            } else if (update.message && update.message.text) {
                chatId = String(update.message.chat.id);
                text = update.message.text.trim();
            } else {
                return new Response("OK");
            }

            // 1. Check User vs Notion
            const isValidUser = await checkNotionUser(env, chatId);
            if (!isValidUser) {
                await sendMessage(env, chatId, "⛔ Tài khoản của bạn chưa được kích hoạt.\nVui lòng liên hệ Admin để thêm vào hệ thống.");
                return new Response("Unauthorized", { status: 200 });
            }

            // 2. Handle Commands & Callbacks
            let mode = "";
            let targetRepo = "";
            let question = "";

            // === GARMIN BOT Commands ===
            if (text.startsWith("/ask")) {
                mode = "ask";
                targetRepo = "garmin";
                question = text.substring(4).trim();
                if (!question) {
                    await sendMessage(env, chatId, "⚠️ Vui lòng nhập câu hỏi sau lệnh /ask.");
                    return new Response("OK");
                }
                await sendMessage(env, chatId, "💬 Đang trả lời...");
            } else if (text === "/daily" || text === "daily" || text === "/report") {
                mode = "daily";
                targetRepo = "garmin";
                await sendMessage(env, chatId, "🚀 Đang lấy báo cáo ngày...");
            } else if (text === "/sleep" || text === "sleep_analysis") {
                mode = "sleep_analysis";
                targetRepo = "garmin";
                await sendMessage(env, chatId, "💤 Đang phân tích giấc ngủ...");
            } else if (text === "/workout" || text === "workout") {
                mode = "workout";
                targetRepo = "garmin";
                await sendMessage(env, chatId, "🏃 Đang phân tích bài tập...");
            } else if (text === "/battery" || text === "battery") {
                mode = "battery";
                targetRepo = "garmin";
                await sendMessage(env, chatId, "🔋 Đang phân tích năng lượng...");
                
            // === UEH NOTION Commands ===
            } else if (text === "/taskreport" || text === "daily-report") {
                mode = "daily-report";
                targetRepo = "ueh";
                await sendMessage(env, chatId, "📊 Đang tạo báo cáo task...");
            } else if (text === "/study" || text === "study-assistant") {
                mode = "study-assistant";
                targetRepo = "ueh";
                await sendMessage(env, chatId, "🎓 Đang tạo bài ôn tập...");
                
            // === General ===
            } else if (text === "/start" || text === "/help" || text === "/menu") {
                const replyMarkup = {
                    inline_keyboard: [
                        [{ text: "📊 Báo cáo Ngày", callback_data: "daily" }],
                        [
                            { text: "💤 Phân tích Ngủ", callback_data: "sleep_analysis" },
                            { text: "🏃 Bài tập", callback_data: "workout" }
                        ],
                        [{ text: "🔋 Bắt mạch Năng lượng", callback_data: "battery" }]
                    ]
                };
                
                await sendMessage(env, chatId, "👋 Chào mừng bạn đến với **Garmin AI Coach**!\nHãy chọn chức năng để bắt đầu:", replyMarkup);
                return new Response("OK");
            } else {
                const replyMarkup = {
                    inline_keyboard: [
                        [{ text: "📊 Báo cáo Ngày", callback_data: "daily" }],
                        [
                            { text: "💤 Phân tích Ngủ", callback_data: "sleep_analysis" },
                            { text: "🏃 Bài tập", callback_data: "workout" }
                        ],
                        [{ text: "🔋 Bắt mạch Năng lượng", callback_data: "battery" }]
                    ]
                };

                await sendMessage(env, chatId, "👋 Tôi chưa hiểu lệnh của bạn.\nHãy gõ `/ask <câu hỏi>` để trò chuyện với AI, hoặc sử dụng menu dưới đây để yêu cầu báo cáo:", replyMarkup);
                return new Response("OK");
            }

            // 3. Trigger GitHub (route to correct repo)
            if (mode && targetRepo) {
                const success = await triggerGitHub(env, mode, chatId, targetRepo, question);
                if (!success) {
                    await sendMessage(env, chatId, "⚠️ Lỗi hệ thống khi gọi Bot. Thử lại sau.");
                }
            }

            return new Response("OK");

        } catch (e) {
            return new Response(`Error: ${e.message}`, { status: 500 });
        }
    },
};

async function checkNotionUser(env, telegramId) {
    const url = `https://api.notion.com/v1/databases/${env.NOTION_DATABASE_ID}/query`;
    const body = {
        filter: {
            property: "Telegram Chat ID",
            rich_text: {
                equals: telegramId
            }
        }
    };

    const resp = await fetch(url, {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${env.NOTION_TOKEN}`,
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        },
        body: JSON.stringify(body)
    });

    if (!resp.ok) {
        console.log("Notion Error:", await resp.text());
        return false;
    }

    const data = await resp.json();
    return data.results.length > 0;
}

async function sendMessage(env, chatId, text, replyMarkup = null) {
    const url = `https://api.telegram.org/bot${env.TG_BOT_TOKEN}/sendMessage`;
    const payload = { chat_id: chatId, text: text, parse_mode: "Markdown" };
    
    if (replyMarkup) {
        payload.reply_markup = replyMarkup;
    }

    await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
}

async function triggerGitHub(env, mode, chatId, targetRepo, question = "") {
    // Route to correct repo
    let owner, repo;
    if (targetRepo === "ueh") {
        owner = env.UEH_GITHUB_OWNER || env.GITHUB_OWNER;
        repo = env.UEH_GITHUB_REPO;
    } else {
        owner = env.GITHUB_OWNER;
        repo = env.GITHUB_REPO;
    }

    console.log("Triggering GitHub for owner:", owner, "repo:", repo);
    console.log("Using token starting with:", env.GITHUB_TOKEN ? env.GITHUB_TOKEN.substring(0, 4) + "..." : "undefined");

    const url = `https://api.github.com/repos/${owner}/${repo}/dispatches`;
    const payload = {
        event_type: "telegram_command",
        client_payload: { mode: mode, user_id: chatId, question: question }
    };

    const resp = await fetch(url, {
        method: "POST",
        headers: {
            "Authorization": `token ${env.GITHUB_TOKEN}`,
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Cloudflare-Worker"
        },
        body: JSON.stringify(payload)
    });

    if (resp.status !== 204) {
        console.error("GitHub Dispatch Error Status:", resp.status);
        console.error("GitHub Dispatch Error Body:", await resp.text());
        return false;
    }
    return true;
}
