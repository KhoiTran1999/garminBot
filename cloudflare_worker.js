export default {
    async fetch(request, env, ctx) {
        if (request.method !== "POST") {
            return new Response("Method not allowed", { status: 405 });
        }

        try {
            const update = await request.json();
            if (!update.message || !update.message.text) return new Response("OK");

            const chatId = String(update.message.chat.id);
            const text = update.message.text.trim();

            // 1. Check User vs Notion
            const isValidUser = await checkNotionUser(env, chatId);
            if (!isValidUser) {
                await sendMessage(env, chatId, "⛔ Tài khoản của bạn chưa được kích hoạt.\nVui lòng liên hệ Admin để thêm vào hệ thống.");
                return new Response("Unauthorized", { status: 200 });
            }

            // 2. Handle Commands
            let mode = "";
            if (text === "/daily" || text === "/report") {
                mode = "daily";
                await sendMessage(env, chatId, "🚀 Đang lấy báo cáo ngày...");
            } else if (text === "/sleep") {
                mode = "sleep_analysis";
                await sendMessage(env, chatId, "💤 Đang phân tích giấc ngủ...");
            } else if (text === "/workout") {
                mode = "workout";
                await sendMessage(env, chatId, "🏃 Đang phân tích bài tập...");
            } else if (text === "/start" || text === "/help") {
                await sendMessage(env, chatId, "✅ Bạn đã được kích hoạt!\nCác lệnh:\n/daily\n/sleep\n/workout");
                return new Response("OK");
            } else {
                return new Response("OK");
            }

            // 3. Trigger GitHub
            const success = await triggerGitHub(env, mode, chatId);
            if (!success) {
                await sendMessage(env, chatId, "⚠️ Lỗi hệ thống khi gọi Bot. Thử lại sau.");
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
    // Check if any active user found
    // Optional: Check 'Active' checkbox property if needed, but existence is good first step
    return data.results.length > 0;
}

async function sendMessage(env, chatId, text) {
    const url = `https://api.telegram.org/bot${env.TG_BOT_TOKEN}/sendMessage`;
    await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, text: text })
    });
}

async function triggerGitHub(env, mode, chatId) {
    const url = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/dispatches`;
    const payload = {
        event_type: "telegram_command",
        client_payload: { mode: mode, user_id: chatId }
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
    return resp.status === 204;
}