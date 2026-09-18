/**
 * AgentForge · P0 阶段交付物端到端全链路自动化集成测试
 * =========================================================
 * 涵盖：
 * 1. [P0-2] 多模型主备倒换与熔断状态监控 (/api/v1/models/status)
 * 2. [P0-1] 知识库异构文档拖拽上传、切片解析与安全删除 (/api/v1/knowledge/*)
 * 3. [P0-3] 部门 Token FinOps 账单核算与标准 CSV 对账单导出 (/api/v1/governance/billing/*)
 * 4. 前端 Vite Web 静态资产与 API 代理连通性
 */

const fs = require('fs');
const path = require('path');

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:6001';
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:6002';

async function runTest(name, fn) {
  process.stdout.write(`⏳ 正在执行测试: [${name}] ... `);
  const start = Date.now();
  try {
    await fn();
    const elapsed = Date.now() - start;
    console.log(`\x1b[32m✔ 通过\x1b[0m (${elapsed}ms)`);
  } catch (err) {
    console.log(`\x1b[31m✘ 失败\x1b[0m: ${err.message}`);
    process.exit(1);
  }
}

async function main() {
  console.log('=' .repeat(65));
  console.log('⚡ 开始执行 AgentForge P0 核心系统集成自动化验证');
  console.log('=' .repeat(65));

  // 1. 测试多模型主备熔断路由状态
  await runTest('P0-2: 多模型主备链路与熔断器健康指标', async () => {
    const res = await fetch(`${BACKEND_URL}/api/v1/models/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.status !== 'success') throw new Error('API 返回 status != success');
    if (!data.cluster || !data.cluster.nodes || data.cluster.nodes.length < 1) {
      throw new Error('未检测到有效的高可用模型节点列表');
    }
    const primary = data.cluster.nodes.find(n => n.priority === 1);
    if (!primary) throw new Error('未找到主模型线路 (priority=1)');
    if (primary.state !== 'CLOSED') throw new Error(`主模型状态异常: ${primary.state}`);
  });

  // 2. 测试知识库已收录文档列表
  await runTest('P0-1: 知识库文档资产与切片元数据查询', async () => {
    const res = await fetch(`${BACKEND_URL}/api/v1/knowledge/documents`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.status !== 'success') throw new Error('API 返回 status != success');
    if (typeof data.total_documents !== 'number' || data.total_documents <= 0) {
      throw new Error('知识库收录文档数应大于 0');
    }
    if (!data.documents || data.documents.length === 0) {
      throw new Error('文档列表为空');
    }
  });

  // 3. 测试知识库文档上传与解析管线
  const testFileName = `p0_test_doc_${Date.now()}.md`;
  await runTest('P0-1: 知识库文档拖拽上传与即时语义分块解析', async () => {
    const docContent = `# 拓维信息企业级核心业务指引\n\n## 一、研发能效标准\n所有 AI 模型服务必须具备主备双回路保障。\n\n## 二、预算与审计\n每个业务部门每月拥有独立的 Token 配额，超出后触发熔断告警。`;
    const blob = new Blob([docContent], { type: 'text/markdown' });
    const formData = new FormData();
    formData.append('file', blob, testFileName);

    const res = await fetch(`${BACKEND_URL}/api/v1/knowledge/upload`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.status !== 'success') throw new Error(`上传失败: ${data.message}`);
    if (!data.file_info || data.file_info.total_chunks < 1) {
      throw new Error('上传文档切片提取失败，chunks 块数不足');
    }
    if (data.file_info.preview_chunks.length < 1) {
      throw new Error('缺失分块切片预览');
    }
  });

  // 4. 测试知识库清理测试文档
  await runTest('P0-1: 知识库文档安全剔除', async () => {
    const res = await fetch(`${BACKEND_URL}/api/v1/knowledge/documents/${encodeURIComponent(testFileName)}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.status !== 'success') throw new Error(`删除失败: ${data.message}`);
  });

  // 5. 测试 FinOps 财务账单汇总
  await runTest('P0-3: 部门 Token 账单核算与工时效益估算', async () => {
    const res = await fetch(`${BACKEND_URL}/api/v1/governance/billing/summary`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.status !== 'success') throw new Error('API 返回 status != success');
    const billing = data.billing;
    if (!billing || typeof billing.total_tokens_consumed !== 'number') {
      throw new Error('billing 结构异常');
    }
    if (!billing.tenants || billing.tenants.length === 0) {
      throw new Error('未检索到部门租户账单');
    }
    const tenant = billing.tenants[0];
    if (typeof tenant.burn_rate_pct !== 'number' || typeof tenant.cost_cny !== 'number') {
      throw new Error('租户预算与折算金额指标缺失');
    }
  });

  // 6. 测试 FinOps CSV 对账单导出
  await runTest('P0-3: 生成带 UTF-8 BOM 财务对账 CSV 文件导出流', async () => {
    const res = await fetch(`${BACKEND_URL}/api/v1/governance/billing/export`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const contentType = res.headers.get('content-type') || '';
    if (!contentType.includes('csv')) {
      throw new Error(`返回 Content-Type 异常: ${contentType}`);
    }
    const arrayBuf = await res.arrayBuffer();
    const bytes = new Uint8Array(arrayBuf.slice(0, 3));
    // 验证原始二进制流精确包含 0xEF 0xBB 0xBF (UTF-8 BOM)
    if (bytes[0] !== 0xef || bytes[1] !== 0xbb || bytes[2] !== 0xbf) {
      throw new Error('导出的 CSV 缺少 UTF-8 BOM 标识 (会导致 Excel 打开中文乱码)');
    }
    const text = new TextDecoder('utf-8').decode(arrayBuf);
    if (!text.includes('交易流水号') || !text.includes('折算金额(¥)')) {
      throw new Error('CSV 对账单表头字段不完整');
    }
  });

  // 7. 测试前端 React Web 服务与统一访问端口 (6002 桥接 & 6000 监听)
  await runTest('前端 React Web 界面访问与端口可达性', async () => {
    // 验证统一安全网关 6002 (有效规避 Chromium 对 6000 端口的 Bad Port 拦截)
    const res = await fetch(FRONTEND_URL);
    if (!res.ok) throw new Error(`统一网关 HTTP 响应码异常: ${res.status}`);
    const html = await res.text();
    if (!html.includes('<div id="root"></div>')) {
      throw new Error('前端根节点缺失');
    }

    // 验证底层 6000 端口原生监听
    const http = require('http');
    await new Promise((resolve, reject) => {
      http.get('http://127.0.0.1:6000', (resp) => {
        if (resp.statusCode === 200) resolve();
        else reject(new Error(`6000 状态码异常: ${resp.statusCode}`));
      }).on('error', reject);
    });
  });

  console.log('=' .repeat(65));
  console.log('\x1b[32m🎉 P0 阶段全部功能端到端全链路验证 100% 通过！\x1b[0m');
  console.log('=' .repeat(65));
}

main();
