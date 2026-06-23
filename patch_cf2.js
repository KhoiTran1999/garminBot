const fs = require('fs');
let code = fs.readFileSync('cloudflare_worker.js', 'utf8');

code = code.replace(
    /await sendMessage\(env, chatId, "🎛 \*\*Dashboard\*\*\r?\nChọn tính năng bạn muốn sử dụng:", \{/,
    'await sendMessage(env, chatId, "🎛 **Dashboard**\nChọn tính năng bạn muốn sử dụng:", {'
);

fs.writeFileSync('cloudflare_worker.js', code);
