const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8000/ws/chat?session_id=test_bge_m3');

ws.on('open', () => {
  ws.send(JSON.stringify({
    message: '根据架构细节，数据接入管道是由什么组件来进行路由分配的？',
    mode: 'fast'
  }));
});

ws.on('message', (data) => {
  console.log(`Received: ${data}`);
});

ws.on('close', () => {
  console.log('Connection closed');
});
