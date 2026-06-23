const fs = require('fs');
let code = fs.readFileSync('cloudflare_worker.js', 'utf8');

// Thêm custom keyboard vào send message
code = code.replace(
    'async function sendMessage(env, chatId, text) {',
    `async function sendMessage(env, chatId, text, replyMarkup = null) {`
);

code = code.replace(
    'body: JSON.stringify({ chat_id: chatId, text: text })',
    `body: JSON.stringify({ chat_id: chatId, text: text, ...(replyMarkup && {reply_markup: replyMarkup}) })`
);

// update welcome message
code = code.replace(
    `await sendMessage(env, chatId,
                    "✅ Bot đã sẵn sàng!\n\n" +
                    "🏃 Garmin:\n" +
                    "/daily - Báo cáo ngày\n" +
                    "/sleep - Phân tích giấc ngủ\n" +
                    "/workout - Phân tích bài tập\n" +
                    "/battery - Phân tích năng lượng\n\n" +
                    "📚 UEH Notion:\n" +
                    "/taskreport - Báo cáo task\n" +
                    "/study - Ôn tập khắc sâu"
                );`,
    `await sendMessage(env, chatId,
                    "✅ Bot đã sẵn sàng!\n\n" +
                    "Bấm nút Dashboard bên dưới để xem menu chức năng.",
                    {
                        keyboard: [[{ text: "📊 Dashboard" }]],
                        resize_keyboard: true,
                        is_persistent: true
                    }
                );`
);

code = code.replace(
    `            } else if (text === "/start" || text === "/help") {`,
    `            } else if (text === "📊 Dashboard" || text === "/dashboard") {
                await sendMessage(env, chatId, "🎛 **Dashboard**\nChọn tính năng bạn muốn sử dụng:", {
                    inline_keyboard: [
                        [{ text: "Báo cáo Ngày", callback_data: "daily" }],
                        [{ text: "Phân tích Ngủ", callback_data: "sleep_analysis" },
                         { text: "Phân tích Tập luyện", callback_data: "workout" }],
                        [{ text: "Bắt mạch Năng lượng (Pin & Stress)", callback_data: "battery" }]
                    ]
                });
                return new Response("OK");
            } else if (text === "/start" || text === "/help") {`
);

fs.writeFileSync('cloudflare_worker.js', code);
