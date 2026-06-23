# Plan to add Persistent Dashboard Keyboard to Telegram Bot

## Requirements
1. Modify `/start` command to send a `ReplyKeyboardMarkup` with "📊 Dashboard" and "📚 UEH Study".
2. Add block to catch "📊 Dashboard" and return the inline keyboard menu for Garmin options.
3. Add block to catch "📚 UEH Study" and return a relevant menu.
4. Keep existing inline callback functionality for Garmin features (`daily`, `sleep_analysis`, etc).

## Implementation Steps for `cloudflare_worker.js`

1. **Update `/start` handler (line 56-70):**
   - Separate `/start` from `/help` or `/menu`.
   - When `text === "/start"`, send a welcome message with a `ReplyKeyboardMarkup`.
   ```javascript
   const replyMarkup = {
       keyboard: [[{ text: "📊 Dashboard" }], [{ text: "📚 UEH Study" }]],
       resize_keyboard: true,
       is_persistent: true
   };
   await sendMessage(env, chatId, "✅ Chào mừng bạn đến với Garmin AI Coach!\nHãy sử dụng menu bên dưới:", replyMarkup);
   ```

2. **Add "📊 Dashboard" handler (or update `/help`/`/menu` to use this):**
   - Catch `text === "📊 Dashboard"`.
   - Send the existing `InlineKeyboardMarkup` that was previously under `/start`.
   ```javascript
   } else if (text === "📊 Dashboard" || text === "/menu" || text === "/help") {
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
       await sendMessage(env, chatId, "Vui lòng chọn chức năng cho Dashboard:", replyMarkup);
       return new Response("OK");
   ```

3. **Add "📚 UEH Study" handler:**
   - Catch `text === "📚 UEH Study"`.
   - Send an appropriate inline keyboard (can be placeholder or define specific callbacks).
   ```javascript
   } else if (text === "📚 UEH Study") {
       // Optionally define inline keyboard for UEH Study here.
       await sendMessage(env, chatId, "Tính năng UEH Study đang phát triển.");
       return new Response("OK");
   ```

4. **Ensure `triggerGitHub` execution logic remains intact:**
   - The current mode logic for `daily`, `sleep_analysis`, `workout`, `battery` handles the inline callbacks correctly and triggers github actions. No changes needed there.
