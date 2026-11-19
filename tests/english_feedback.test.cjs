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

function memoryStorage() {
  const values = new Map();
  return {
    get length() { return values.size; },
    key: index => [...values.keys()][index] ?? null,
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: key => values.delete(key),
  };
}

function page(fetch, sendBeacon, storage = {}) {
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
  const window = { ...element(), ...storage, setInterval, clearInterval, setTimeout, scrollTo() {} };
  const document = {
    getElementById: get, querySelectorAll: () => [], createElement: element,
    createTextNode: element, createDocumentFragment: element
  };
  vm.runInNewContext(script, {
    window, document, fetch, navigator: { sendBeacon }, performance, crypto: { randomUUID },
    Blob, TextDecoder, AbortController, DOMException, clearTimeout,
  });
  return { get, window, ask: (question = 'What is intrinsic value?') => {
    get('question').value = question;
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
      finish = (features = {}) => {
        send({ ...features, type: 'done', answer: 'Completed answer', validation: { status: 'references_checked', issues: [] } });
        controller.close();
      };
    } }), { headers: { 'Content-Type': 'text/event-stream' } });
  });
  ui.ask();
  await tick();
  assert.equal(ui.get('feedback').hidden, true);
  finish({ feedback_available: true });
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
  // A follow-up can land on a process serving the old completion format.
  ui.ask();
  await tick();
  finish();
  await tick();
  assert.equal(ui.get('answer-wrap').hidden, false);
  assert.equal(ui.get('follow-up').hidden, false);
  assert.equal(ui.get('feedback').hidden, true);
  await ui.get('feedback').emit('submit');
  assert.equal(calls.length, 4);
});

test('Stop and pagehide send a single request-linked departure during a pending answer', async () => {
  for (const action of ['stop', 'pagehide']) {
    const beacons = [];
    let request, fallback;
    const ui = page(async (url, options) => {
      if (url.endsWith('/left')) { fallback = options; return new Response(null, { status: 404 }); }
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
    assert.equal(ui.get('question').value, 'What is intrinsic value?');
    assert.equal(ui.get('error-title').textContent, 'Stopped');
  }
});

test('reload can continue a saved chat, while a new chat sends an empty history', async () => {
  const calls = [];
  const storage = { localStorage: memoryStorage(), sessionStorage: memoryStorage() };
  const fetch = async (url, options) => {
    assert.equal(url, '/api/english/ask');
    calls.push(JSON.parse(options.body));
    const done = { type: 'done', answer: 'Answer ' + calls.length, validation: {status: 'references_checked'} };
    return new Response('data: ' + JSON.stringify(done) + '\n\n', {
      headers: { 'Content-Type': 'text/event-stream' }
    });
  };

  const first = page(fetch, undefined, storage);
  first.ask('What is the circle of competence?');
  await tick();
  first.ask('Can it grow?');
  await tick();
  assert.equal(calls[1].history[0].content, calls[0].question);

  const restored = page(fetch, undefined, storage);
  assert.equal(restored.get('asked-question').textContent, 'Can it grow?');
  restored.ask('Did he ever get this wrong?');
  await tick();
  assert.deepEqual(calls[2].history.map(message => message.content),
    [calls[0].question, 'Answer 1', calls[1].question, 'Answer 2']);

  restored.get('new-question').emit('click');
  restored.ask('How does Buffett evaluate a stock?');
  await tick();
  assert.deepEqual(calls[3].history, []);
  assert.equal(storage.localStorage.length, 2);
});

test('a storage quota error retains completed answers in the current tab', async () => {
  const localStorage = memoryStorage();
  let failWrite = false;
  const write = localStorage.setItem;
  localStorage.setItem = (key, value) => {
    if (failWrite) throw new Error('quota exceeded');
    write(key, value);
  };
  const calls = [];
  const ui = page(async (url, options) => {
    calls.push(JSON.parse(options.body));
    const done = {type:'done', answer:'Answer ' + calls.length, validation:{status:'references_checked'}};
    return new Response('data: ' + JSON.stringify(done) + '\n\n', {
      headers: {'Content-Type':'text/event-stream'}
    });
  }, undefined, {localStorage, sessionStorage:memoryStorage()});

  ui.ask('First question?');
  await tick();
  failWrite = true;
  ui.ask('Second question?');
  await tick();
  assert.equal(ui.get('storage-error').hidden, false);
  failWrite = false;
  ui.ask('Third question?');
  await tick();
  ui.ask('Fourth question?');
  await tick();
  assert.deepEqual(calls[3].history.filter(m => m.role === 'user').map(m => m.content),
    ['First question?', 'Second question?', 'Third question?']);
});
