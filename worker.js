/**
 * Cloudflare Worker for Telegram File Server Bot
 * Deploy this directly in Cloudflare Dashboard
 */

// ---------------------- ENVIRONMENT VARIABLES ---------------------- //
// Set these in Cloudflare Dashboard > Workers > Settings > Environment Variables

const BOT_TOKEN = env.BOT_TOKEN;
const STORAGE_CHANNEL = env.STORAGE_CHANNEL;
const F_CHANNEL = env.F_CHANNEL;
const JOIN_LINK = env.JOIN_LINK;
const ADMIN_IDS = env.ADMIN_IDS ? env.ADMIN_IDS.split(',').map(id => parseInt(id.trim())) : [];

// ---------------------- HELPER FUNCTIONS ---------------------- //

async function checkUserJoined(userId) {
  try {
    const response = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/getChatMember`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: F_CHANNEL,
        user_id: userId
      })
    });
    
    const data = await response.json();
    if (data.ok) {
      const status = data.result.status;
      return ['member', 'administrator', 'creator'].includes(status);
    }
    return false;
  } catch (error) {
    console.error('Error checking user join:', error);
    return false;
  }
}

async def sendMessage(chatId, text, replyMarkup = null) {
  const payload = {
    chat_id: chatId,
    text: text,
    parse_mode: 'HTML'
  };
  
  if (replyMarkup) {
    payload.reply_markup = replyMarkup;
  }

  return await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}

async function editMessage(chatId, messageId, text, replyMarkup = null) {
  const payload = {
    chat_id: chatId,
    message_id: messageId,
    text: text,
    parse_mode: 'HTML'
  };
  
  if (replyMarkup) {
    payload.reply_markup = replyMarkup;
  }

  return await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/editMessageText`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}

async function copyMessage(fromChatId, messageId, toChatId) {
  return await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/copyMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from_chat_id: fromChatId,
      message_id: messageId,
      chat_id: toChatId
    })
  }).then(r => r.json());
}

function isAdmin(userId) {
  return ADMIN_IDS.includes(userId);
}

// ---------------------- COMMAND HANDLERS ---------------------- //

async function handleStart(update) {
  const message = update.message;
  const userId = message.from.id;
  const args = message.text.split(' ').slice(1);

  if (args.length === 0) {
    await sendMessage(userId, '🟢 Bot Online!\nSend any media to generate a shareable link.');
    return;
  }

  try {
    const msgId = parseInt(args[0]);
    const userJoined = await checkUserJoined(userId);

    if (!userJoined) {
      const replyMarkup = {
        inline_keyboard: [
          [{ text: '✅ Join Now', url: JOIN_LINK }],
          [{ text: '♻️ Retry', callback_data: `retry_${msgId}` }]
        ]
      };

      await sendMessage(
        userId,
        'You must join our channel to access this file.\n\nJoin the channel and click Retry.',
        replyMarkup
      );
      return;
    }

    // User joined, send file
    await copyMessage(STORAGE_CHANNEL, msgId, userId);

  } catch (error) {
    console.error('Error in handleStart:', error);
    await sendMessage(userId, '❌ File not found!');
  }
}

async function handleCallbackQuery(update) {
  const query = update.callback_query;
  const userId = query.from.id;
  const data = query.data;

  if (data.startsWith('retry_')) {
    const msgId = parseInt(data.split('_')[1]);
    const userJoined = await checkUserJoined(userId);

    if (!userJoined) {
      const replyMarkup = {
        inline_keyboard: [
          [{ text: '✅ Join Now', url: JOIN_LINK }],
          [{ text: '♻️ Retry', callback_data: `retry_${msgId}` }]
        ]
      };

      await editMessage(
        userId,
        query.message.message_id,
        "You still haven't joined the channel. Please join first and then click Retry.",
        replyMarkup
      );
    } else {
      await editMessage(userId, query.message.message_id, '✅ Verification successful! Sending file...');
      await copyMessage(STORAGE_CHANNEL, msgId, userId);
    }
  }
}

async function handleMedia(update) {
  const message = update.message;
  const userId = message.from.id;

  if (!isAdmin(userId)) {
    await sendMessage(userId, '❌ Sorry! Only admins can upload files.');
    return;
  }

  try {
    const response = await copyMessage(message.chat.id, message.message_id, STORAGE_CHANNEL);
    
    if (response.ok) {
      const fileMsgId = response.result.message_id;
      const botResponse = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/getMe`);
      const botData = await botResponse.json();
      const botUsername = botData.result.username;
      const deepLink = `https://t.me/${botUsername}?start=${fileMsgId}`;

      await sendMessage(userId, `📥 <b>Shareable Link:</b>\n${deepLink}`);
    } else {
      await sendMessage(userId, '❌ Error uploading file!');
    }
  } catch (error) {
    console.error('Error in handleMedia:', error);
    await sendMessage(userId, '❌ Error uploading file!');
  }
}

// ---------------------- MAIN HANDLER ---------------------- //

export default {
  async fetch(request) {
    if (request.method === 'POST') {
      try {
        const update = await request.json();

        // Handle /start command
        if (update.message && update.message.text && update.message.text.startsWith('/start')) {
          await handleStart(update);
        }
        // Handle callback queries (button clicks)
        else if (update.callback_query) {
          await handleCallbackQuery(update);
        }
        // Handle media uploads
        else if (update.message && (update.message.photo || update.message.video || update.message.document)) {
          await handleMedia(update);
        }

        return new Response('OK', { status: 200 });
      } catch (error) {
        console.error('Error:', error);
        return new Response('Error', { status: 500 });
      }
    }

    return new Response('Bot is running', { status: 200 });
  }
};
