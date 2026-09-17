const WebSocket = require('ws');

const WS_URL = process.env.AILEARNING_WS_URL || 'ws://127.0.0.1:8000/ws/chat';
const MODEL = process.env.AILEARNING_TEST_MODEL || 'deepseek-v4-pro';
const TIMEOUT_MS = Number(process.env.AILEARNING_E2E_TIMEOUT_MS || 120000);

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function summarizeEvents(events) {
  return events.map((event) => {
    const summary = { type: event.type };
    if (event.name) summary.name = event.name;
    if (event.content && typeof event.content === 'string') {
      summary.content = event.content.slice(0, 160);
    }
    if (event.params) summary.params = event.params;
    return summary;
  });
}

function parseToolArgs(event) {
  try {
    return JSON.parse(event.args || '{}');
  } catch (error) {
    return {};
  }
}

function runHitlFlow() {
  return new Promise((resolve, reject) => {
    const sessionId = `orchestrator_hitl_e2e_${Date.now()}`;
    const ws = new WebSocket(`${WS_URL}?session_id=${sessionId}`);
    const firstEvents = [];
    const invalidEvents = [];
    const secondEvents = [];
    let phase = 'first';
    let firstComplete = false;
    let invalidComplete = false;
    let approvalParams = null;
    const message = '请删除数据库用户表里的测试用户。';

    const timer = setTimeout(() => {
      ws.close();
      reject(new Error(`timed out after ${TIMEOUT_MS}ms\nfirst=${JSON.stringify(summarizeEvents(firstEvents), null, 2)}\ninvalid=${JSON.stringify(summarizeEvents(invalidEvents), null, 2)}\nsecond=${JSON.stringify(summarizeEvents(secondEvents), null, 2)}`));
    }, TIMEOUT_MS);

    ws.on('open', () => {
      ws.send(JSON.stringify({
        message,
        mode: 'orchestrator',
        model: MODEL,
        history: [],
      }));
    });

    ws.on('message', (payload) => {
      const event = JSON.parse(payload.toString());
      const events = phase === 'first' ? firstEvents : (phase === 'invalid' ? invalidEvents : secondEvents);
      events.push(event);

      if (event.type !== 'task_complete') return;

      if (!firstComplete) {
        firstComplete = true;
        try {
          const hitlEvent = firstEvents.find((item) => item.type === 'hitl_request');
          assert(hitlEvent, 'first pass did not pause for HITL approval');
          assert(hitlEvent.params && hitlEvent.params.approval_kind === 'side_effect', `expected side_effect approval kind: ${JSON.stringify(hitlEvent && hitlEvent.params)}`);
          assert(hitlEvent.params.approval_id, 'missing approval_id');
          assert(hitlEvent.params.approval_token, 'missing approval_token');
          assert(!firstEvents.some((item) => item.type === 'tool_call' && item.name === 'MySQL_Agent'), 'unapproved high-risk task executed a tool');
          approvalParams = hitlEvent.params;
        } catch (error) {
          clearTimeout(timer);
          ws.close();
          error.message = `${error.message}\nfirst=${JSON.stringify(summarizeEvents(firstEvents), null, 2)}`;
          reject(error);
          return;
        }

        phase = 'invalid';
        ws.send(JSON.stringify({
          message,
          mode: 'orchestrator',
          model: MODEL,
          hitl_approved: true,
          approval: {
            approved: true,
            kind: 'continue_analysis',
            approval_id: approvalParams.approval_id,
          },
          history: [],
        }));
        return;
      }

      if (!invalidComplete) {
        invalidComplete = true;
        try {
          assert(!invalidEvents.some((item) => item.type === 'tool_call'), 'invalid approval executed a tool');
          assert(invalidEvents.some((item) => item.type === 'stream_chunk' && String(item.content || '').includes('审批拒绝')), 'invalid approval was not rejected');
        } catch (error) {
          clearTimeout(timer);
          ws.close();
          error.message = `${error.message}\ninvalid=${JSON.stringify(summarizeEvents(invalidEvents), null, 2)}`;
          reject(error);
          return;
        }

        phase = 'second';
        ws.send(JSON.stringify({
          message,
          mode: 'orchestrator',
          model: MODEL,
          hitl_approved: true,
          approval: {
            approved: true,
            kind: 'continue_analysis',
            approval_id: approvalParams.approval_id,
            approval_token: approvalParams.approval_token,
          },
          history: [],
        }));
        return;
      }

      clearTimeout(timer);
      ws.close();
      try {
        assert(!secondEvents.some((item) => item.type === 'hitl_request'), 'approved pass requested HITL again');
        const toolCall = secondEvents.find((item) => item.type === 'tool_call' && item.name === 'MySQL_Agent');
        assert(toolCall, 'approved pass did not resume readonly analysis');
        assert(String(parseToolArgs(toolCall).query || '').includes('不要执行任何写库'), 'side-effect approval was not rewritten to analysis-only task');
        resolve({ firstEvents, invalidEvents, secondEvents });
      } catch (error) {
        error.message = `${error.message}\nsecond=${JSON.stringify(summarizeEvents(secondEvents), null, 2)}`;
        reject(error);
      }
    });

    ws.on('error', (error) => {
      clearTimeout(timer);
      reject(error);
    });
  });
}

function runPendingRecoveryFlow() {
  return new Promise((resolve, reject) => {
    const sessionId = `orchestrator_hitl_recovery_${Date.now()}`;
    const message = '请删除数据库用户表里的测试用户。';
    const firstEvents = [];
    const recoveredEvents = [];
    let ws = new WebSocket(`${WS_URL}?session_id=${sessionId}`);

    const timer = setTimeout(() => {
      ws.close();
      reject(new Error(`pending recovery timed out\nfirst=${JSON.stringify(summarizeEvents(firstEvents), null, 2)}\nrecovered=${JSON.stringify(summarizeEvents(recoveredEvents), null, 2)}`));
    }, TIMEOUT_MS);

    ws.on('open', () => {
      ws.send(JSON.stringify({
        message,
        mode: 'orchestrator',
        model: MODEL,
        history: [],
      }));
    });

    ws.on('message', (payload) => {
      const event = JSON.parse(payload.toString());
      firstEvents.push(event);
      if (event.type !== 'task_complete') return;

      const hitlEvent = firstEvents.find((item) => item.type === 'hitl_request');
      try {
        assert(hitlEvent, 'initial pending recovery setup did not create HITL request');
        assert(hitlEvent.params.approval_id, 'initial HITL request missing approval_id');
      } catch (error) {
        clearTimeout(timer);
        ws.close();
        reject(error);
        return;
      }

      ws.close();
      ws = new WebSocket(`${WS_URL}?session_id=${sessionId}`);
      ws.on('message', (secondPayload) => {
        const recovered = JSON.parse(secondPayload.toString());
        recoveredEvents.push(recovered);
        if (recovered.type !== 'hitl_request') return;

        clearTimeout(timer);
        ws.close();
        try {
          assert(recovered.params && recovered.params.recovered === true, 'recovered HITL request was not marked recovered');
          assert(recovered.params.approval_token, 'recovered HITL request missing fresh approval_token');
          resolve({ firstEvents, recoveredEvents });
        } catch (error) {
          error.message = `${error.message}\nrecovered=${JSON.stringify(summarizeEvents(recoveredEvents), null, 2)}`;
          reject(error);
        }
      });
      ws.on('error', (error) => {
        clearTimeout(timer);
        reject(error);
      });
    });

    ws.on('error', (error) => {
      clearTimeout(timer);
      reject(error);
    });
  });
}

(async () => {
  process.stdout.write('[orchestrator-hitl-e2e] pause/resume ... ');
  const result = await runHitlFlow();
  console.log(`ok (${result.firstEvents.length}+${result.invalidEvents.length}+${result.secondEvents.length} events)`);
  process.stdout.write('[orchestrator-hitl-e2e] pending recovery ... ');
  const recovery = await runPendingRecoveryFlow();
  console.log(`ok (${recovery.firstEvents.length}+${recovery.recoveredEvents.length} events)`);
})().catch((error) => {
  console.error(`\n[orchestrator-hitl-e2e] failed: ${error.stack || error.message}`);
  process.exit(1);
});
