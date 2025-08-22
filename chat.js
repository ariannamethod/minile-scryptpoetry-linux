let networkUrl = window.location.origin;
if (!networkUrl || networkUrl === 'null' || window.location.protocol === 'file:') {
  networkUrl = 'http://localhost:8000';
}

const chat = document.getElementById('chat');
const msgInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');

function addMsg(text, cls) {
  const div = document.createElement('div');
  div.textContent = text;
  div.className = 'msg ' + cls;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

document.getElementById('input-area').addEventListener('submit', e => {
  e.preventDefault();
  const text = msgInput.value.trim();
  if (!text) return;
  addMsg('> ' + text, 'sent');
  msgInput.value = '';
  fetch(networkUrl + '/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: text,
  })
    .then(r => r.text())
    .then(t => addMsg(t, 'received'))
    .catch(err => addMsg('Error: ' + err.message, 'received'));
});
