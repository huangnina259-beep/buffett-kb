// Exercise the shipped English page with a model-free SSE response.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { randomUUID } = require('node:crypto');

const html = fs.readFileSync(path.join(__dirname, '../frontend/english.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const tick = () => new Promise(resolve => setImmediate(resolve));

function page(fetch, sendBeacon) {
  function element() {
    const handlers = {};
    return {
      value: '', textContent: '', hidden: false, checked: false, disabled: false,
      classList: { toggle() {} }, addEventListener(name, handler) { handlers[name] = handler; },
      emit(name) { return handlers[name]({ preventDefault() {} }); },
      setAttribute() {}, append() {}, replaceChildren() {}, focus() {}, reset() {}
    };
  }
  const byId = new Map();
  const get = id => {
    if (!byId.has(id)) byId.set(id, element());
    return byId.get(id);
  };
  const window = { ...element(), setInterval, clearInterval, setTimeout };
  const document = {
    getElementById: get, querySelectorAll: () => [], createElement: element,
    createTextNode: element, createDocumentFragment: element
  };
  vm.runInNewContext(script, {
    window, document, fetch, navigator: { sendBeacon }, performance, crypto: { randomUUID },
    Blob, TextDecoder, AbortController, DOMException, clearTimeout,
  });
  return { get, window, ask: () => {
    get('question').value = 'What is intrinsic value?';
    get('question-form').emit('submit');
  } };
}

test('only final answers offer feedback; corrections stay tied to the completed request', async () => {
  const calls = [];
  let finish, save;
  const ui = page(async (url, options) => {
    calls.push([url, JSON.parse(options.body)]);
    if (url.endsWith('/feedback')) return new Promise(resolve => { save = resolve; });
    return new Response(new ReadableStream({ start(controller) {
      const send = data => controller.enqueue(new TextEncoder().encode('data: ' + JSON.stringify(data) + '\n\n'));
      send({ type: 'token', text: 'Draft' });
      finish = () => {
        send({ type: 'done', answer: 'Completed answer', validation: { status: 'references_checked', issues: [] } });
        controller.close();
      };
    } }), { headers: { 'Content-Type': 'text/event-stream' } });
  });
  ui.ask();
  await tick();
  assert.equal(ui.get('feedback').hidden, true);
  finish();
  await tick();
  assert.equal(ui.get('feedback').hidden, false);
  assert.equal(calls[0][1].entrypoint, 'english_form');
  ui.get('feedback-no').checked = true;
  ui.get('feedback').emit('input');
  assert.equal(ui.get('feedback-note-label').hidden, false);
  ui.get('feedback-note').value = '  Needs more context. ';
  const sent = ui.get('feedback').emit('submit');
  assert.deepEqual(calls[1], ['/api/english/feedback', {
    request_id: calls[0][1].request_id, helpful: false, note: 'Needs more context.'
  }]);
  save(new Response(null, { status: 503 }));
  await sent;
  assert.match(ui.get('feedback-status').textContent, /try again/);
  const retry = ui.get('feedback').emit('submit');
  save(new Response(null, { status: 204 }));
  await retry;
  assert.match(ui.get('feedback-status').textContent, /Feedback sent/);
  ui.window.emit('pagehide');
  assert.equal(calls.length, 3);
});

test('Stop and pagehide send a single request-linked departure during a pending answer', async () => {
  for (const action of ['stop', 'pagehide']) {
    const beacons = [];
    let request, fallback;
    const ui = page(async (url, options) => {
      if (url.endsWith('/left')) { fallback = options; return new Response(null, { status: 204 }); }
      request = JSON.parse(options.body);
      return new Promise((resolve, reject) => options.signal.addEventListener('abort', () => reject(new Error('Stopped'))));
    }, (url, body) => { beacons.push([url, body]); return action === 'stop'; });
    ui.ask();
    if (action === 'pagehide') ui.window.emit('pagehide');
    ui.get('stop').emit('click');
    ui.window.emit('pagehide');
    await tick();
    assert.equal(beacons.length, 1);
    const [url, blob] = beacons[0];
    const data = JSON.parse(await blob.text());
    assert.equal(url, '/api/english/left');
    assert.equal(data.request_id, request.request_id);
    assert.equal(data.event, action);
    assert.ok(Number.isInteger(data.elapsed_ms) && data.elapsed_ms >= 0);
    if (action === 'pagehide') {
      assert.deepEqual(JSON.parse(fallback.body), data);
      assert.equal(fallback.keepalive, true);
    } else assert.equal(fallback, undefined);
    assert.equal(ui.get('feedback').hidden, true);
  }
});
