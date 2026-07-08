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

            const trimmedText = text.trim();
            const firstSpaceIndex = trimmedText.indexOf(" ");
            let command = firstSpaceIndex !== -1 ? trimmedText.substring(0, firstSpaceIndex) : trimmedText;
            let cmdArgs = firstSpaceIndex !== -1 ? trimmedText.substring(firstSpaceIndex).trim() : "";

            // Check if this is a reply to the askForUserNote prompt
            let isReplyToPrompt = false;
            let promptMode = "";
            if (update.message && update.message.reply_to_message && update.message.reply_to_message.text) {
                const replyText = update.message.reply_to_message.text;
                if (replyText.includes("Bạn đã chọn tính năng")) {
                    isReplyToPrompt = true;
                    if (replyText.includes("[Phân tích Giấc ngủ]")) promptMode = "sleep_analysis";
                    else if (replyText.includes("[Sức khỏe & Đề xuất Tập]")) promptMode = "daily";
                    else if (replyText.includes("[Phân tích Buổi tập]")) promptMode = "workout";
                    else if (replyText.includes("[Bắt mạch Năng lượng]")) promptMode = "battery";
                }
            }

            // === Check Reply to Prompt ===
            if (isReplyToPrompt && promptMode) {
                mode = promptMode;
                targetRepo = "garmin";
                question = text;

                // Delete Message 1 (ForceReply prompt)
                const msg1Id = update.message.reply_to_message.message_id;
                await deleteMessage(env, chatId, msg1Id);

                // Delete Message 2 (Skip button prompt, usually msg1Id + 1)
                await deleteMessage(env, chatId, msg1Id + 1);

                // Delete the user's reply message
                await deleteMessage(env, chatId, update.message.message_id);

                await sendMessage(env, chatId, `🚀 Đang phân tích kèm thông tin cập nhật mới nhất của bạn...`, null, true);
            }
            // === Check Callback run: ===
            else if (text.startsWith("run:")) {
                const parts = text.split(":");
                mode = parts[1];
                targetRepo = "garmin";
                question = "";

                // Delete Message 2 (contains the button)
                if (update.callback_query && update.callback_query.message) {
                    const msg2Id = update.callback_query.message.message_id;
                    await deleteMessage(env, chatId, msg2Id);
                }

                // Delete Message 1 (ForceReply prompt)
                if (parts[2]) {
                    const msg1Id = parseInt(parts[2]);
                    await deleteMessage(env, chatId, msg1Id);
                }

                await sendMessage(env, chatId, `🚀 Bắt đầu phân tích dữ liệu...`, null, true);
            }
            // === Check Garmin Inline Buttons or Clean Commands (No Args) ===
            else if ((command === "/daily" || command === "/report" || command === "daily") && !cmdArgs) {
                await askForUserNote(env, chatId, "daily", "Sức khỏe & Đề xuất Tập");
                return new Response("OK");
            } else if ((command === "/sleep" || command === "sleep_analysis") && !cmdArgs) {
                await askForUserNote(env, chatId, "sleep_analysis", "Phân tích Giấc ngủ");
                return new Response("OK");
            } else if ((command === "/workout" || command === "/activities" || command === "workout") && !cmdArgs) {
                await askForUserNote(env, chatId, "workout", "Phân tích Buổi tập");
                return new Response("OK");
            } else if ((command === "/battery" || command === "battery") && !cmdArgs) {
                await askForUserNote(env, chatId, "battery", "Bắt mạch Năng lượng");
                return new Response("OK");
            }
            // === Regular Garmin Commands (With Args) / Ask ===
            else if (command === "/ask") {
                mode = "ask";
                targetRepo = "garmin";
                question = cmdArgs;
                if (!question) {
                    await sendMessage(env, chatId, "⚠️ Vui lòng nhập câu hỏi sau lệnh /ask.");
                    return new Response("OK");
                }
                await sendMessage(env, chatId, "💬 Đang trả lời...", null, true);
            } else if (command === "/daily" || command === "daily" || command === "/report") {
                mode = "daily";
                targetRepo = "garmin";
                question = cmdArgs;
                await sendMessage(env, chatId, "🚀 Đang lấy báo cáo ngày...", null, true);
            } else if (command === "/sleep" || command === "sleep_analysis") {
                mode = "sleep_analysis";
                targetRepo = "garmin";
                question = cmdArgs;
                await sendMessage(env, chatId, "💤 Đang phân tích giấc ngủ...", null, true);
            } else if (command === "/workout" || command === "/activities" || command === "workout") {
                mode = "workout";
                targetRepo = "garmin";
                question = cmdArgs;
                await sendMessage(env, chatId, "🏃 Đang phân tích bài tập...", null, true);
            } else if (command === "/battery" || command === "battery") {
                mode = "battery";
                targetRepo = "garmin";
                question = cmdArgs;
                await sendMessage(env, chatId, "🔋 Đang phân tích năng lượng...", null, true);

            // === UEH NOTION Commands ===
            } else if (text === "/taskreport" || text === "daily-report") {
                mode = "daily-report";
                targetRepo = "ueh";
                await sendMessage(env, chatId, "📊 Đang tạo báo cáo task...", null, true);
            } else if (text === "/study" || text === "study-assistant") {
                mode = "study-assistant";
                targetRepo = "ueh";
                await sendMessage(env, chatId, "🎓 Đang tạo bài ôn tập...", null, true);

            // === General ===
            } else if (text === "/start" || text === "/help" || text === "/menu") {
                const replyMarkup = {
                    inline_keyboard: [
                        [{ text: "📊 Sức khỏe & Đề xuất Tập", callback_data: "daily" }],
                        [
                            { text: "💤 Phân tích Ngủ", callback_data: "sleep_analysis" },
                            { text: "🏃 Phân tích Buổi tập", callback_data: "workout" }
                        ],
                        [{ text: "🔋 Bắt mạch Năng lượng", callback_data: "battery" }]
                    ]
                };

                await sendMessage(env, chatId, "👋 Chào mừng bạn đến với **Garmin AI Coach**!\nHãy chọn chức năng để bắt đầu:", replyMarkup);
                return new Response("OK");
            } else {
                const replyMarkup = {
                    inline_keyboard: [
                        [{ text: "📊 Sức khỏe & Đề xuất Tập", callback_data: "daily" }],
                        [
                            { text: "💤 Phân tích Ngủ", callback_data: "sleep_analysis" },
                            { text: "🏃 Phân tích Buổi tập", callback_data: "workout" }
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

async function sendMessage(env, chatId, text, replyMarkup = null, disableNotification = false) {
    const url = `https://api.telegram.org/bot${env.TG_BOT_TOKEN}/sendMessage`;
    const payload = {
        chat_id: chatId,
        text: text,
        parse_mode: "Markdown",
        disable_notification: disableNotification
    };

    if (replyMarkup) {
        payload.reply_markup = replyMarkup;
    }

    const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(`Telegram sendMessage failed: ${resp.status} - ${errText}`);
    }
}

async function triggerGitHub(env, mode, chatId, targetRepo, question = "") {
    // Route to correct repo
    let owner, repo;
    if (targetRepo === "ueh") {
        owner = env.UEH_GITHUB_OWNER || env.GITHUB_OWNER || "KhoiTran1999";
        repo = env.UEH_GITHUB_REPO || "uehNotion";
    } else {
        owner = env.GITHUB_OWNER || "KhoiTran1999";
        repo = env.GITHUB_REPO || "garminBot";
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

async function deleteMessage(env, chatId, messageId) {
    const url = `https://api.telegram.org/bot${env.TG_BOT_TOKEN}/deleteMessage`;
    try {
        await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chat_id: chatId, message_id: messageId })
        });
    } catch (e) {
        console.log("Error deleting message:", e);
    }
}

async function askForUserNote(env, chatId, mode, featureName) {
    const url = `https://api.telegram.org/bot${env.TG_BOT_TOKEN}/sendMessage`;

    const payload1 = {
        chat_id: chatId,
        text: `✍️ Bạn đã chọn tính năng [${featureName}]. Bạn có muốn cập nhật thêm thông tin gì mới nhất hôm nay không (ví dụ: tối qua ngủ muộn, cơ thể mệt mỏi, đau chân...)?\n\n👉 Hãy gõ vào ô chat phía dưới để cập nhật.`,
        reply_markup: {
            force_reply: true,
            selective: true
        }
    };

    const resp1 = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload1)
    });

    let msg1Id = null;
    if (resp1.ok) {
        const data1 = await resp1.json();
        msg1Id = data1.result.message_id;
    }

    const payload2 = {
        chat_id: chatId,
        text: `Hoặc nếu không có gì mới để cập nhật, hãy nhấn nút dưới đây để phân tích luôn:`,
        reply_markup: {
            inline_keyboard: [
                [{ text: "❌ Tôi không có gì mới để cập nhật", callback_data: msg1Id ? `run:${mode}:${msg1Id}` : `run:${mode}` }]
            ]
        }
    };

    await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload2)
    });
}
