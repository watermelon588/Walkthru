import { publicDestination, snapshot } from '../lib/snapshot';

function link(href: string) {
  const a = document.createElement('a');
  a.href = href;
  a.textContent = 'Explore';
  return a;
}

test('captures route and section destinations without converting labels into paths', () => {
  expect(publicDestination(link('/work'))).toBe('/work');
  expect(publicDestination(link('/#destinations'))).toBe('/#destinations');
  document.body.replaceChildren(link('/work'));
  expect(snapshot(document, { geometry: false }).elements[0]?.destination).toBe('/work');
  expect(publicDestination(document.createElement('button'))).toBeUndefined();
});

test.each(['https://other.invalid/work', 'javascript:alert(1)', 'mailto:owner@example.com',
  '/work?project=1', '/work#token=private', '/owner%40example.com', '/1234567890', '/sk_live_1234567890abcdefghijk'])
('does not expose ambiguous or private destination %s', (href) => {
  expect(publicDestination(link(href))).toBeUndefined();
});

test('cross-origin base elements cannot disguise an external destination', () => {
  const base = document.createElement('base');
  base.href = 'https://other.invalid/';
  document.head.append(base);
  try { expect(publicDestination(link('/work'))).toBeUndefined(); }
  finally { base.remove(); }
});
