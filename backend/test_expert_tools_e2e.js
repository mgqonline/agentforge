const WebSocket = require('ws');

const WS_URL = process.env.AILEARNING_WS_URL || 'ws://127.0.0.1:8000/ws/chat';
const MODEL = process.env.AILEARNING_TEST_MODEL || 'deepseek-v4-pro';
const TIMEOUT_MS = Number(process.env.AILEARNING_E2E_TIMEOUT_MS || 120000);

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function connectAndRun(testCase) {
  return new Promise((resolve, reject) => {
    const sessionId = `expert_tools_e2e_${testCase.name}_${Date.now()}`;
    const ws = new WebSocket(`${WS_URL}?session_id=${sessionId}`);
    const events = [];
    const timer = setTimeout(() => {
      ws.close();
      reject(new Error(`[${testCase.name}] timed out after ${TIMEOUT_MS}ms`));
    }, TIMEOUT_MS);

    ws.on('open', () => {
      ws.send(JSON.stringify({
        message: testCase.message,
        mode: 'expert',
        model: MODEL,
        history: [],
      }));
    });

    ws.on('message', (payload) => {
      const event = JSON.parse(payload.toString());
      events.push(event);

      if (event.type === 'task_complete') {
        clearTimeout(timer);
        ws.close();
        try {
          testCase.assert(events);
          resolve(events);
        } catch (error) {
          error.message = `${error.message}\nEvents: ${JSON.stringify(summarizeEvents(events), null, 2)}`;
          reject(error);
        }
      }
    });

    ws.on('error', (error) => {
      clearTimeout(timer);
      reject(error);
    });
  });
}

function findToolResult(events, name) {
  return events.find((event) => event.type === 'tool_call_result' && event.name === name);
}

function summarizeEvents(events) {
  return events.map((event) => {
    const summary = { type: event.type };
    if (event.name) summary.name = event.name;
    if (event.result) summary.result = event.result;
    if (event.content && typeof event.content === 'string') {
      summary.content = event.content.slice(0, 160);
    }
    return summary;
  });
}

const testCases = [
  {
    name: 'rag',
    message: '请调用知识库工具查询：如何使用 RAG 架构实现内部知识库？',
    assert(events) {
      assert(events.some((event) => event.type === 'tool_call' && event.name === 'search_knowledge_base'), 'missing search_knowledge_base tool_call');
      const resultEvent = findToolResult(events, 'search_knowledge_base');
      assert(resultEvent, 'missing search_knowledge_base tool_call_result');
      assert(resultEvent.result && resultEvent.result.ok === true, `RAG tool failed: ${JSON.stringify(resultEvent && resultEvent.result)}`);
      assert(events.some((event) => event.type === 'stream_end'), 'missing stream_end');
    },
  },
  {
    name: 'sql_readonly',
    message: '请调用数据库查询工具，只读查询数据库里有哪些表。',
    assert(events) {
      assert(events.some((event) => event.type === 'tool_call' && event.name === 'query_sql_database'), 'missing query_sql_database tool_call');
      const resultEvent = findToolResult(events, 'query_sql_database');
      assert(resultEvent, 'missing query_sql_database tool_call_result');
      assert(resultEvent.result && resultEvent.result.sql_type === 'readonly', `SQL tool did not report readonly: ${JSON.stringify(resultEvent && resultEvent.result)}`);
      assert(events.some((event) => event.type === 'stream_end'), 'missing stream_end');
    },
  },
  {
    name: 'sql_write_block',
    message: '请调用数据库查询工具删除用户表里的测试用户。',
    assert(events) {
      assert(events.some((event) => event.type === 'tool_call' && event.name === 'query_sql_database'), 'missing query_sql_database tool_call');
      const resultEvent = findToolResult(events, 'query_sql_database');
      assert(resultEvent, 'missing query_sql_database tool_call_result');
      assert(resultEvent.result && resultEvent.result.ok === false, `write intent was not blocked: ${JSON.stringify(resultEvent && resultEvent.result)}`);
      assert(String(resultEvent.result.error || '').includes('not allowed'), `unexpected write block error: ${JSON.stringify(resultEvent.result)}`);
      assert(events.some((event) => event.type === 'stream_end'), 'missing stream_end');
    },
  },
];

(async () => {
  for (const testCase of testCases) {
    process.stdout.write(`[expert-tools-e2e] ${testCase.name} ... `);
    const events = await connectAndRun(testCase);
    console.log(`ok (${events.length} events)`);
  }
})().catch((error) => {
  console.error(`\n[expert-tools-e2e] failed: ${error.stack || error.message}`);
  process.exit(1);
});
