import { executeAsync, type Step } from '../lib/execute';
import { publicState, snapshot } from '../lib/snapshot';

const base: Step = { action: 'scroll', thought: '', target_id: null, text: null, confusion: 0 };
function metrics(el: Element, values: Record<string, number>) {
  for (const [key, value] of Object.entries(values)) Object.defineProperty(el, key, { value, writable: true, configurable: true });
}
function pane(label = 'Projects') {
  const el = document.createElement('section');
  el.setAttribute('aria-label', label);
  el.style.overflowY = 'auto';
  el.style.overflowX = 'auto';
  el.innerHTML = '<button>Edit project</button>';
  document.body.append(el);
  metrics(el, { scrollTop: 0, scrollLeft: 0, scrollHeight: 1000, clientHeight: 200, scrollWidth: 900, clientWidth: 300 });
  el.scrollBy = vi.fn((options: ScrollToOptions) => {
    el.scrollTop = Math.min(800, Math.max(0, el.scrollTop + (options.top ?? 0)));
    el.scrollLeft = Math.min(600, Math.max(0, el.scrollLeft + (options.left ?? 0)));
  }) as typeof el.scrollBy;
  return el;
}
function observe() { return snapshot(document, { geometry: false }); }
function scrollStep(id = 1): Step { return { ...base, scroll_container_id: id, observation_revision: observe().revision }; }

beforeEach(() => { document.body.innerHTML = ''; });
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

test('separate pane IDs include window and associate duplicate controls with their nearest pane', () => {
  pane('Alpha'); pane('Beta');
  const obs = observe();
  expect(obs.navigation_version).toBe(3);
  expect(obs.scroll_containers?.map(c => [c.id, c.label])).toEqual([[0, 'Page'], [1, 'Alpha'], [2, 'Beta']]);
  expect(obs.elements.map(e => e.scroll_container_id)).toEqual([1, 2]);
  expect(obs.scroll_containers?.[1]).toMatchObject({ can_down: true, can_up: false, can_right: true, can_left: false });
});

test('pane count and masked labels share the bounded observation context budget', () => {
  for (let i = 0; i < 15; i++) pane(`Owner person${i}@example.test ` + 'name '.repeat(60));
  const obs = observe();
  expect(obs.scroll_containers).toHaveLength(12);
  expect(obs.scroll_containers_truncated).toBe(true);
  expect(JSON.stringify(obs)).not.toContain('@example.test');
  const count = obs.elements.reduce((n, e) => n + (e.row?.length ?? 0) + (e.region?.length ?? 0), 0) + obs.scroll_containers!.reduce((n, c) => n + c.label.length, 0);
  expect(count).toBeLessThanOrEqual(6000);
});

test.each(['down', 'up', 'right', 'left'] as const)('bounded pane %s measures actual offsets and caps distance to its viewport', async direction => {
  const el = pane(); el.scrollTop = 400; el.scrollLeft = 300;
  const result = await executeAsync({ ...scrollStep(), scroll_direction: direction, scroll_distance: 1000 }, document);
  expect(el.scrollBy).toHaveBeenCalledOnce();
  expect(result.executor_result?.status).toBe('moved');
  const before = result.executor_result!.before!, after = result.executor_result!.after!;
  expect(after.top - before.top).toBe(direction === 'down' ? 170 : direction === 'up' ? -170 : 0);
  expect(after.left - before.left).toBe(direction === 'right' ? 255 : direction === 'left' ? -255 : 0);
});

test('edge/no-scroll reports no progress without claiming a site defect', async () => {
  const el = pane(); el.scrollTop = 800;
  const result = await executeAsync(scrollStep(), document);
  expect(result).toMatchObject({ ok: true, executor_result: { status: 'no_progress', before: { top: 800 }, after: { top: 800 } } });
});

test('legacy window scrolling keeps its safe viewport fallback and explicit window binds revision', async () => {
  let top = 0;
  vi.spyOn(window, 'scrollY', 'get').mockImplementation(() => top);
  metrics(document.documentElement, { scrollHeight: 4000 });
  vi.spyOn(window, 'scrollBy').mockImplementation((options: number | ScrollToOptions, y?: number) => { top += typeof options === 'number' ? y ?? 0 : options.top ?? 0; });
  const legacy = await executeAsync(base, document);
  expect(legacy.executor_result).toMatchObject({ container_id: 0, status: 'moved' });
  expect(top).toBe(Math.min(1000, window.innerHeight * .85));
  const explicit = await executeAsync({ ...base, scroll_container_id: 0 }, document);
  expect(explicit.note).toMatch(/^stale target:/);
});

test.each(['replaced', 'renamed', 'hidden', 'reparented', 'overflow changed', 'new revision'])('a %s pane refuses scroll before dispatch', async change => {
  const el = pane(); const step = scrollStep();
  if (change === 'replaced') el.replaceWith(el.cloneNode(true));
  if (change === 'renamed') el.setAttribute('aria-label', 'Different workspace');
  if (change === 'hidden') el.hidden = true;
  if (change === 'reparented') { const wrap = document.createElement('div'); document.body.append(wrap); wrap.append(el); }
  if (change === 'new revision') observe();
  if (change === 'overflow changed') el.style.overflowY = 'hidden';
  expect((await executeAsync(step, document)).note).toMatch(/^stale target:/);
  expect(el.scrollBy).not.toHaveBeenCalled();
});

test('a newly blocking modal refuses nested and legacy window scrolling', async () => {
  const el = pane(); const step = scrollStep();
  document.body.insertAdjacentHTML('beforeend', '<div role="dialog" aria-modal="true">Confirm</div>');
  expect((await executeAsync(step, document)).note).toMatch(/^stale target:/);
  expect((await executeAsync(base, document)).note).toMatch(/^stale target:/);
  expect(el.scrollBy).not.toHaveBeenCalled();
});

test('reversed axes keep signed observations and safely decline unsupported movement', async () => {
  const el = pane(); el.style.direction = 'rtl'; el.scrollLeft = -100;
  const step = scrollStep();
  expect(observe().scroll_containers?.[1]).toMatchObject({ left: -100, can_left: false, can_right: false });
  step.observation_revision = observe().revision;
  const result = await executeAsync({ ...step, scroll_direction: 'right' }, document);
  expect(result.executor_result?.status).toBe('no_progress');
  expect(el.scrollBy).not.toHaveBeenCalled();
});

test('a vertically scrollable pane does not expose or move its intentionally clipped horizontal content', async () => {
  const el = pane(); el.style.overflowX = 'hidden';
  const obs = observe();
  expect(obs.scroll_containers?.[1]).toMatchObject({ can_down: true, can_left: false, can_right: false });
  const result = await executeAsync({ ...base, scroll_container_id: 1, scroll_direction: 'right', observation_revision: obs.revision }, document);
  expect(result.executor_result).toMatchObject({ status: 'no_progress', before: { left: 0 }, after: { left: 0 } });
  expect(el.scrollBy).not.toHaveBeenCalled();
});

function waitStep(condition: Step['wait_condition'] = 'settled', timeout = 1000): Step {
  return { ...base, action: 'wait', observation_revision: observe().revision, wait_condition: condition, wait_timeout_ms: timeout };
}
async function advance(result: Promise<unknown>, ms: number) { await vi.advanceTimersByTimeAsync(ms); return result; }

test('text wait detects delayed public results without dispatching mutations again', async () => {
  vi.useFakeTimers(); const el = pane(); const step = waitStep('text_changed');
  const result = executeAsync(step, document);
  setTimeout(() => document.body.insertAdjacentHTML('beforeend', '<div role="status">Loaded 12 projects</div>'), 200);
  expect(await advance(result, 300)).toMatchObject({ executor_result: { status: 'changed' } });
  expect(el.scrollBy).not.toHaveBeenCalled();
});

test('unchanged waits have an explicit timeout and do not rotate snapshot revisions', async () => {
  vi.useFakeTimers(); pane(); const step = waitStep('text_changed', 250);
  expect(await advance(executeAsync(step, document), 250)).toMatchObject({ executor_result: { status: 'timeout', elapsed_ms: 250 } });
  // The same captured revision remains valid after observation polling.
  expect((await executeAsync({ ...step, action: 'scroll', scroll_container_id: 1 }, document)).executor_result?.status).toBe('moved');
});

test('settled waits ignore attribute churn and private input edits while observing public state', async () => {
  vi.useFakeTimers(); document.body.innerHTML = '<input value="privateOne"><p>Ready</p>';
  const step = waitStep(); const result = executeAsync(step, document);
  setTimeout(() => { document.querySelector('input')!.value = 'privateTwo'; document.querySelector('p')!.style.opacity = '.9'; }, 100);
  expect(await advance(result, 350)).toMatchObject({ executor_result: { status: 'settled' } });
  expect(publicState(document).text).not.toMatch(/privateOne|privateTwo/);
});

test('visible busy state and short deadlines cannot be reported as settled', async () => {
  vi.useFakeTimers(); document.body.innerHTML = '<div aria-busy="true">Loading</div>';
  expect(await advance(executeAsync(waitStep('settled', 400), document), 400)).toMatchObject({ executor_result: { status: 'timeout' } });
  document.body.innerHTML = '<p>Ready</p>';
  expect(await advance(executeAsync(waitStep('settled', 100), document), 100)).toMatchObject({ executor_result: { status: 'timeout' } });
});

test('owner abort and operation budget immediately stop waits and prevent scroll dispatch', async () => {
  vi.useFakeTimers(); const el = pane(); const controller = new AbortController();
  const result = executeAsync(waitStep('text_changed', 5000), document, {}, controller.signal);
  setTimeout(() => controller.abort(), 100);
  expect(await advance(result, 100)).toMatchObject({ executor_result: { status: 'aborted', elapsed_ms: 100 } });
  expect((await executeAsync(scrollStep(), document, {}, controller.signal)).executor_result).toMatchObject({ status: 'aborted', container_id: 1 });
  expect(el.scrollBy).not.toHaveBeenCalled();
  expect(await advance(executeAsync(waitStep('text_changed'), document, { deadline_ms: Date.now() + 150 }), 150)).toMatchObject({ executor_result: { status: 'aborted' } });
});

test('waiting on a stale observation stops before polling', async () => {
  const step = waitStep(); observe();
  expect((await executeAsync(step, document)).note).toMatch(/^stale target:/);
});

test('a slow public-state read cannot claim a change beyond the timeout and preserves elapsed overrun', async () => {
  document.body.innerHTML = '<p>Before</p>';
  const step = waitStep('text_changed', 100);
  document.querySelector('p')!.textContent = 'Changed';
  let now = 10000;
  vi.spyOn(Date, 'now').mockImplementation(() => now);
  const nodes = document.body.childNodes;
  vi.spyOn(document.body, 'childNodes', 'get').mockImplementation(() => { now += 6000; return nodes; });
  const result = await executeAsync(step, document);
  expect(result.executor_result).toMatchObject({ status: 'timeout', elapsed_ms: 12000 });
});

test('a slow public-state read that crosses the operation deadline reports abort', async () => {
  document.body.innerHTML = '<p>Before</p>';
  const step = waitStep('text_changed', 1000);
  let now = 10000;
  vi.spyOn(Date, 'now').mockImplementation(() => now);
  const nodes = document.body.childNodes;
  vi.spyOn(document.body, 'childNodes', 'get').mockImplementation(() => { now += 300; return nodes; });
  const result = await executeAsync(step, document, { deadline_ms: 10150 });
  expect(result.executor_result).toMatchObject({ status: 'aborted', elapsed_ms: 300 });
});
