import { snapshot } from '../lib/snapshot';

function rect(el: Element, x: number, y: number, w: number, h: number) {
  vi.spyOn(el, 'getBoundingClientRect').mockReturnValue({ x, y, width: w, height: h, top: y, bottom: y + h, left: x, right: x + w, toJSON: () => ({}) });
}
function metrics(el: Element, values: Record<string, number>) {
  for (const [key, value] of Object.entries(values)) Object.defineProperty(el, key, { value, configurable: true });
}
function fixture() {
  document.body.innerHTML = '<a href="#work">Explore</a><section id="work"><h2>Selected projects</h2><button>Open project</button></section>';
  return { link: document.querySelector('a')!, section: document.querySelector('section')! };
}
beforeEach(() => { document.body.innerHTML = ''; });
afterEach(() => { vi.restoreAllMocks(); });

test('document identity is stable while snapshots change and new Documents are distinct', () => {
  fixture();
  const first = snapshot(document, { geometry: false }), second = snapshot(document, { geometry: false });
  expect(first.document_id).toMatch(/^[a-f0-9-]{36}$/);
  expect(second.document_id).toBe(first.document_id);
  expect(second.revision).not.toBe(first.revision);
  const iframe = document.createElement('iframe'); document.body.append(iframe);
  expect(snapshot(iframe.contentDocument!, { geometry: false }).document_id).not.toBe(first.document_id);
});

test('unmeasured snapshots disclose relationships without claiming visibility', () => {
  fixture();
  const obs = snapshot(document, { geometry: false });
  expect(obs.elements[0]?.section_target).toBe('work');
  expect(obs.sections).toEqual([{ key: 'work', label: 'Selected projects' }]);
  expect(obs.elements.every(e => !e.reveal)).toBe(true);
});

test('single aria-controls relationships work; multiple, private and duplicate IDs stay unknown', () => {
  document.body.innerHTML = '<button aria-controls="panel">Open</button><section id="panel" aria-label="Details"></section>';
  expect(snapshot(document, { geometry: false }).elements[0]?.section_target).toBe('panel');
  document.body.innerHTML += '<section id="panel"></section>';
  expect(snapshot(document, { geometry: false }).sections).toEqual([]);
  document.body.innerHTML = '<button aria-controls="alpha beta">Open</button><section id="alpha"></section><section id="beta"></section>';
  expect(snapshot(document, { geometry: false }).sections).toEqual([]);
  document.body.innerHTML = '<button aria-controls="sk_live_1234567890abcdefghijk">Open</button><section id="sk_live_1234567890abcdefghijk"></section>';
  expect(snapshot(document, { geometry: false }).sections).toEqual([]);
});

test('a link to another document does not establish a section relationship', () => {
  document.body.innerHTML = '<a href="/different#work">Work</a><section id="work"></section>';
  expect(snapshot(document, { geometry: false }).sections).toEqual([]);
});

test('hidden controlled panels retain a relationship but cannot claim visibility', () => {
  document.body.innerHTML = '<button aria-controls="panel">Open details</button><section id="panel" hidden><h2>Details</h2></section>';
  rect(document.querySelector('button')!, 10, 10, 100, 30);
  const obs = snapshot(document);
  expect(obs.elements[0]?.section_target).toBe('panel');
  expect(obs.sections?.[0]).toMatchObject({ key: 'panel', in_view: false });
  expect(obs.sections?.[0]?.label).toBe('');
});

test('visible sections require measured clipping and an unobscured hit', () => {
  const { link, section } = fixture();
  rect(link, 10, 10, 90, 30); rect(section, 10, 100, 400, 200);
  Object.defineProperty(document, 'elementFromPoint', { value: vi.fn(() => section), configurable: true });
  expect(snapshot(document).sections?.[0]).toMatchObject({ in_view: true, occluded: false });
  const cover = document.createElement('aside'); document.body.append(cover);
  Object.defineProperty(document, 'elementFromPoint', { value: vi.fn(() => cover), configurable: true });
  expect(snapshot(document).sections?.[0]).toMatchObject({ in_view: true, occluded: true });
});

test('offscreen sections get a direction only when the observed window can move', () => {
  const { link, section } = fixture(); rect(link, 10, 10, 90, 30); rect(section, 10, 1600, 400, 200);
  metrics(document.documentElement, { scrollHeight: 2600, clientHeight: 768, scrollWidth: 1024, clientWidth: 1024 });
  const obs = snapshot(document);
  expect(obs.sections?.[0]).toMatchObject({ in_view: false, reveal_direction: 'down', scroll_container_id: 0 });
  rect(section, 1800, 1600, 400, 200);
  expect(snapshot(document).sections?.[0]?.reveal_direction).toBeUndefined();
});

test('section capture is capped and refuses uniqueness when its ID scan is incomplete', () => {
  document.body.innerHTML = Array.from({ length: 30 }, (_, i) => `<a href="#part${i}">Part ${i}</a><section id="part${i}" aria-label="Part ${i}"></section>`).join('');
  const obs = snapshot(document, { geometry: false });
  expect(obs.sections).toHaveLength(24); expect(obs.sections_truncated).toBe(true);
  document.body.innerHTML = '<a href="#work">Work</a><section id="work"></section>' + '<div></div>'.repeat(2001);
  const bounded = snapshot(document, { geometry: false });
  expect(bounded.sections).toEqual([]); expect(bounded.sections_truncated).toBe(true);
  expect(bounded.elements[0]?.section_target).toBeUndefined();
});
