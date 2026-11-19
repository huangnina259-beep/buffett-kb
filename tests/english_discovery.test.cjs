const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'frontend/english.html'), 'utf8');
const catalog = JSON.parse(fs.readFileSync(path.join(root, 'data/source_contexts.json')));
const originals = new Map(catalog.contexts.map(source => [source.context_id, source]));

class Element {
  children = [];
  attributes = {};
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(type, handler) { this[type] = handler; }
}

test('explore questions and inspect their indexed originals without starting a chat', () => {
  const window = {};
  const document = { createElement: () => new Element() };
  const bank = html.match(/<script id="meeting-questions">([\s\S]*?)<\/script>/)[1];
  vm.runInNewContext(bank, { document, window });

  const container = new Element();
  const asked = [], previews = [];
  window.CompounderQuestions.renderStarters(container,
    (question, context) => asked.push({ question, context }),
    (item, button) => previews.push({ item, button }));
  const [header, filters, list] = container.children;
  assert.ok(list.children.length > 3 && list.children.length < originals.size);
  const initial = list.children.length;

  header.children.find(child => child.className === 'discovery-more').click();
  assert.ok(list.children.length > initial);
  const titles = new Set();
  for (const row of list.children) {
    const [question, source] = row.children;
    source.click();
    const preview = previews.at(-1);
    assert.equal(preview.button, source);
    assert.equal(preview.item.url, originals.get(preview.item.context).source_url);
    assert.equal(asked.length, titles.size);
    question.click();
    assert.deepEqual(asked.at(-1), { question: question.textContent, context: preview.item.context });
    titles.add(question.textContent);
  }
  assert.equal(titles.size, list.children.length);
  const total = list.children.length;
  let grouped = 0;
  for (const filter of filters.children.slice(1)) {
    filter.click();
    assert.equal(filter.attributes['aria-pressed'], 'true');
    assert.ok(list.children.length > 0 && list.children.length < total);
    grouped += list.children.length;
  }
  assert.equal(grouped, total);
});
