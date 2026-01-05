/**
 * Cloudflare Worker: Telegram Global Command Handler (User Specific Trigger)
 * 
 * Chức năng:
 * 1. Nhận Webhook từ Telegram.
 * 2. Parse lệnh (/daily, /sleep, ...) và lấy `user_id`.
 * 3. Gọi GitHub Action (repository_dispatch), truyền `user_id` vào client_payload.
 */

export default {
  async fetch(request, env, ctx) {
    // 1. Chỉ chấp nhận POST request
    if (request.method !== 'POST') {
      return new Response('Method Not Allowed', { status: 405 });
    }

    try {
      const payload = await request.json();

      // 2. Validate Telegram Secret Token (Nếu có cài đặt)
      // if (request.headers.get('X-Telegram-Bot-Api-Secret-Token') !== env.TELEGRAM_SECRET_TOKEN) {
      //   return new Response('Unauthorized', { status: 403 });
      // }

      // 3. Xử lý message
      if (payload.message && payload.message.text) {
        const text = payload.message.text;
        const chatId = payload.message.chat.id;
        const userId = payload.message.from.id; // Lấy ID người gửi
        const userName = payload.message.from.first_name;

        console.log(`Received command: ${text} from ${userName} (${userId})`);

        let mode = null;

        // Map lệnh sang mode của main.py
        if (text.startsWith('/daily')) {
          mode = 'daily';
        } else if (text.startsWith('/sleep')) {
          mode = 'sleep_analysis';
        } else if (text.startsWith('/workout')) {
          mode = 'workout';
        }

        if (mode) {
          // 4. Gọi GitHub Action
          const success = await triggerGithubAction(env, mode, userId);
          
          if (success) {
            await sendTelegramMessage(env, chatId, `🚀 Đang chạy lệnh *${mode}* cho ${userName}... Vui lòng đợi!`);
          } else {
            await sendTelegramMessage(env, chatId, `⚠️ Lỗi gọi GitHub Action. Vui lòng thử lại.`);
          }
        } 
        // else {
        //   // Handle unknown commands if necessary
        // }
      }

      return new Response('OK');
    } catch (e) {
      console.error(e);
      return new Response('Error', { status: 500 });
    }
  },
};

/**
 * Gọi GitHub Repository Dispatch Event
 */
async function triggerGithubAction(env, mode, userId) {
  const url = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/dispatches`;

  const body = {
    event_type: 'telegram_command',
    client_payload: {
      mode: mode,
      user_id: userId, // TRUYỀN USER ID SANG GITHUB
      timestamp: new Date().toISOString()
    }
  };

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.GITHUB_TOKEN}`,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'Cloudflare-Worker'
    },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    console.log(`GitHub API Error: ${response.status} ${response.statusText}`);
    const text = await response.text();
    console.log(text);
    return false;
  }
  return true;
}

/**
 * Gửi tin nhắn phản hồi về Telegram
 */
async function sendTelegramMessage(env, chatId, text) {
  const url = `https://api.telegram.org/bot${env.TG_BOT_TOKEN}/sendMessage`;
  await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text: text,
      parse_mode: 'Markdown'
    })
  });
}
