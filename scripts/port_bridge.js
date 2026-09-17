const http = require('http');

/**
 * AgentForge · 双端口无缝桥接服务 (Port Bridge)
 * 作用：兼容历史 6002 端口访问习惯，将 http://localhost:6002 透明双向代理至 http://localhost:6000
 * 零第三方依赖，纯 Node.js 标准库实现。
 */

const TARGET_PORT = 6000;
const LISTEN_PORT = 6002;

const server = http.createServer((clientReq, clientRes) => {
  const options = {
    hostname: '127.0.0.1',
    port: TARGET_PORT,
    path: clientReq.url,
    method: clientReq.method,
    headers: {
      ...clientReq.headers,
      host: `localhost:${TARGET_PORT}`
    }
  };

  const proxy = http.request(options, (targetRes) => {
    clientRes.writeHead(targetRes.statusCode, targetRes.headers);
    targetRes.pipe(clientRes, { end: true });
  });

  proxy.on('error', (err) => {
    // 若 6000 尚未就绪，做友好提示并引导
    clientRes.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    clientRes.end(`
      <!DOCTYPE html>
      <html>
      <head><meta charset="utf-8"><title>AgentForge 页面跳转</title></head>
      <body style="background:#111; color:#fff; font-family:sans-serif; text-align:center; padding:50px;">
        <h2>⚡ 正在跳转至 AgentForge 智炼工坊...</h2>
        <p style="color:#aaa;">如果页面未自动跳转，请直接点击下方链接：</p>
        <p><a href="http://localhost:6000" style="color:#3b82f6; font-size:18px;">http://localhost:6000</a></p>
        <script>setTimeout(() => { window.location.href = "http://localhost:6000"; }, 1000);</script>
      </body>
      </html>
    `);
  });

  clientReq.pipe(proxy, { end: true });
});

// 处理 WebSocket Upgrade 协议升级
server.on('upgrade', (req, socket, head) => {
  const proxySocket = http.request({
    hostname: '127.0.0.1',
    port: TARGET_PORT,
    path: req.url,
    method: req.method,
    headers: {
      ...req.headers,
      host: `localhost:${TARGET_PORT}`
    }
  });

  proxySocket.on('upgrade', (proxyRes, upstreamSocket, proxyHead) => {
    socket.write(
      `HTTP/1.1 101 Switching Protocols\r\n` +
      Object.keys(proxyRes.headers).map(k => `${k}: ${proxyRes.headers[k]}`).join('\r\n') +
      '\r\n\r\n'
    );
    upstreamSocket.pipe(socket);
    socket.pipe(upstreamSocket);
  });

  proxySocket.on('error', () => {
    socket.destroy();
  });

  proxySocket.end();
});

server.listen(LISTEN_PORT, '0.0.0.0', () => {
  console.log(`🚀 [PortBridge] 兼容通道已开启: http://localhost:${LISTEN_PORT} -> http://localhost:${TARGET_PORT}`);
});
