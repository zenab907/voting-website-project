/**
 * DEMS Chatbot — Frontend (v5)
 * Quick buttons stay permanently visible — only opacity changes during fetch.
 */

var chatOpen    = false;
var currentLang = localStorage.getItem('dems_lang') || 'en';

/* CSRF helper */
function getCsrfToken() {
  var name = 'csrftoken';
  var cookies = document.cookie.split(';');
  for (var i = 0; i < cookies.length; i++) {
    var c = cookies[i].trim();
    if (c.startsWith(name + '=')) {
      return decodeURIComponent(c.slice(name.length + 1));
    }
  }
  var el = document.querySelector('[name=csrfmiddlewaretoken]');
  return el ? el.value : '';
}

/* Quick buttons: dim while loading, restore after reply */
function quickBtnsLoading() {
  var qbs = document.getElementById('quick-btns');
  if (!qbs) return;
  qbs.style.opacity       = '0.5';
  qbs.style.pointerEvents = 'none';
}

function quickBtnsReady() {
  var qbs = document.getElementById('quick-btns');
  if (!qbs) return;
  qbs.style.opacity       = '1';
  qbs.style.pointerEvents = 'auto';
}

/* Chat open/close */
function toggleChat() {
  chatOpen = !chatOpen;
  var win    = document.getElementById('chatbot-window');
  var unread = document.getElementById('chat-unread');
  var icon   = document.getElementById('chat-bubble-icon');
  if (!win) return;

  if (chatOpen) {
    win.classList.remove('chatbot-hidden');
    win.classList.add('chatbot-open');
    if (unread) unread.style.display = 'none';
    if (icon)   icon.textContent = 'x';
    var input = document.getElementById('chat-input');
    if (input) setTimeout(function() { input.focus(); }, 100);
  } else {
    win.classList.add('chatbot-hidden');
    win.classList.remove('chatbot-open');
    if (icon) icon.textContent = 'chat';
  }
}

/* Message rendering */
function appendMessage(text, role) {
  var msgs = document.getElementById('chat-messages');
  if (!msgs) return;
  var div    = document.createElement('div');
  div.className = 'chat-msg ' + role;
  var bubble = document.createElement('div');
  bubble.className = 'chat-msg-bubble';
  bubble.innerHTML = text;
  div.appendChild(bubble);
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function appendTyping() {
  var msgs = document.getElementById('chat-messages');
  if (!msgs) return;
  var div  = document.createElement('div');
  div.className = 'chat-msg bot';
  div.id        = 'typing-indicator';
  div.innerHTML = '<div class="chat-msg-bubble"><span class="typing-dot">.</span><span class="typing-dot">.</span><span class="typing-dot">.</span></div>';
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function removeTyping() {
  var el = document.getElementById('typing-indicator');
  if (el) el.parentNode && el.parentNode.removeChild(el);
}

/* Send message */
async function sendMessage() {
  var input = document.getElementById('chat-input');
  var text  = (input ? input.value : '').trim();
  if (!text) return;

  appendMessage(escapeHtml(text), 'user');
  if (input) input.value = '';

  quickBtnsLoading();
  appendTyping();

  try {
    var resp = await fetch('/api/chatbot/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken':  getCsrfToken()
      },
      body: JSON.stringify({ message: text })
    });

    var data = await resp.json();
    removeTyping();

    if (data.success && data.reply) {
      appendMessage(data.reply, 'bot');
    } else {
      appendMessage(
        currentLang === 'ar'
          ? 'حدث خطأ. يرجى المحاولة لاحقاً.'
          : 'Something went wrong. Please try again.',
        'bot'
      );
    }

  } catch (err) {
    removeTyping();
    appendMessage('Network error. Is the server running?', 'bot');
  }

  /* Always restore quick buttons — happens whether fetch succeeded or failed */
  quickBtnsReady();

  /* Scroll to bottom */
  var msgs = document.getElementById('chat-messages');
  if (msgs) msgs.scrollTop = msgs.scrollHeight;
}

/* Quick button click */
function sendQuick(btn) {
  var attr = currentLang === 'ar' ? 'data-ar' : 'data-en';
  var text = btn.getAttribute(attr) || btn.textContent;
  var input = document.getElementById('chat-input');
  if (input) input.value = text;
  sendMessage();
}

/* Utilities */
function escapeHtml(str) {
  return str
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;');
}

/* Enter key support */
document.addEventListener('DOMContentLoaded', function() {
  var inp = document.getElementById('chat-input');
  if (inp) {
    inp.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }
});
