const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8000/ws/chat?session_id=test_query_exact');

ws.on('open', () => {
  ws.send(JSON.stringify({
    message: '请帮我查一下，AI 实验室目前的员工叫什么名字？他今年多少岁了？',
    mode: 'fast'
  }));
});

ws.on('message', (data) => {
  console.log(`Received: ${data}`);
});

ws.on('close', () => {
  console.log('Connection closed');
});
