const WebSocket = require('ws');
const ws = new WebSocket('ws://127.0.0.1:8000/ws/chat?session_id=test_query');
ws.on('open', () => {
  ws.send(JSON.stringify({
    message: 'AI 实验室目前的员工叫什么名字？他今年多少岁了？',
    mode: 'expert',
    model: 'deepseek-v4-pro',
    history: []
  }));
});
ws.on('message', (data) => {
  console.log('Received:', data.toString());
  const msg = JSON.parse(data.toString());
  if (msg.type === 'stream_end' || msg.type === 'task_complete') {
    ws.close();
  }
});
