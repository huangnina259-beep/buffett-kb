const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../frontend/gym.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
function harness(fetch) {
  const elements = {};
  const document = {
    getElementById(id) { return elements[id] ||= {value: '', style: {}, hidden: true, disabled: false}; },
  };
  const context = vm.createContext({document, fetch, navigator: {}, setTimeout});
  vm.runInContext(script, context);
  vm.runInContext("currentCase = 'cocacola'; lang = 'cn';", context);
  document.getElementById('answerInput').value = '我还不知道，需要查阅资料。';
  return { context, elements, run: code => vm.runInContext(code, context) };
}
test('failed feedback preserves answer and round; retry stores one answer', async () => {
  let fail = true;
  const h = harness(async () => ({ ok: !fail, json: async () => ({feedback: '请查阅收入来源。', key_concepts: []}) }));
  await h.run('submitAnswer()');
  assert.equal(h.run('answers.length'), 0);
  assert.equal(h.run('currentRound'), 0);
  assert.equal(h.elements.answerInput.value, '我还不知道，需要查阅资料。');
  assert.equal(h.elements.answerError.hidden, false);
  assert.equal(h.elements.submitBtn.disabled, false);
  fail = false;
  await h.run('submitAnswer()');
  assert.equal(h.run('answers.length'), 1);
  assert.equal(h.run('feedbacks.length'), 1);
  assert.equal(h.elements.answerError.hidden, true);
});
test('empty model output is retryable, never replaced with canned praise', async () => {
  const h = harness(async () => ({ok: true, json: async () => ({feedback: ''})}));
  await h.run('submitAnswer()');
  assert.equal(h.run('answers.length'), 0);
  assert.equal(h.elements.answerError.hidden, false);
});
test('skip stores no synthetic feedback', () => {
  const h = harness(async () => { throw new Error('must not request'); });
  h.run('nextRound = () => { currentRound++; }; skipRound();');
  assert.equal(h.run('answers[0]'), '');
  assert.equal(h.run('feedbacks[0].feedback'), '');
  assert.equal(h.run('currentRound'), 1);
});
