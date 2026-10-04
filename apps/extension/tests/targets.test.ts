import { execute, type Step } from '../lib/execute';
import { snapshot } from '../lib/snapshot';

function observe(html: string) {
  document.body.innerHTML = html;
  return snapshot(document, { geometry: false });
}

function click(observation_revision?: string, target_id = 1): Step {
  return { action: 'click', thought: '', target_id, text: null, confusion: 0, observation_revision };
}

test('duplicate Edit controls carry their own row and named region', () => {
  const obs = observe('<main aria-label="Projects"><table><tr><td>Alpha project</td><td><button>Edit</button></td></tr><tr><td>Beta project</td><td><button>Edit</button></td></tr></table></main>');
  expect(obs.elements.map(e => e.row)).toEqual(['Alpha project Edit', 'Beta project Edit']);
  expect(obs.elements.every(e => e.region === 'main: Projects')).toBe(true);
});

test('additional context excludes field values and redacts before truncating', () => {
  const obs = observe('<main aria-label="Contact owner@example.test"><ul><li>Visible item <textarea>private textarea</textarea><select><option>private option</option></select><span contenteditable="true">private draft</span><input value="private input"><button>Edit</button></li></ul></main>');
  const context = obs.elements.map(e => `${e.region ?? ''} ${e.row ?? ''}`).join(' ');
  expect(context).not.toMatch(/private|owner@example/);
  expect(context).toContain('[email]');
  expect(JSON.stringify(obs)).not.toMatch(/private textarea|private option|private draft|private input/);
});

test('editable values inside alerts and notices never enter the observation', () => {
  const obs = observe('<div role="alert">Required <textarea>private alert</textarea></div><div role="status">Saved <span contenteditable="true">private notice</span></div>');
  expect(obs.errors).toEqual(['Required']);
  expect(obs.notices).toEqual(['Saved']);
  expect(JSON.stringify(obs)).not.toContain('private');
});

test('CSS-hidden private text is absent from the whole observation', () => {
  const obs = observe('<style>.concealed { display:none }.faded { opacity:0 }</style><main><li>Alpha <span class="concealed">privateCSS</span><span style="visibility:hidden">privateVisibility</span><span class="faded">privateOpacity</span><button>Edit</button></li></main>');
  expect(JSON.stringify(obs)).not.toMatch(/privateCSS|privateVisibility|privateOpacity/);
  expect(obs.text).toBe('Alpha Edit');
});

test('hidden ancestors of region headings and labelledBy names cannot leak text', () => {
  const obs = observe('<main><div style="display:none"><h2>privateHeading</h2><span id="secretName">privateName</span></div><button aria-labelledby="secretName">Visible fallback</button></main>');
  expect(JSON.stringify(obs)).not.toMatch(/privateHeading|privateName/);
  expect(obs.elements[0]!.text).toBe('Visible fallback');
});

test('URL credentials, query values, fragments and opaque tokens are masked before context truncation', () => {
  const token = 'aB9_'.repeat(12);
  const obs = observe(`<li>https://person:privatePassword@site.test/path?token=privateQuery#privateFragment ${token}<button>Edit</button></li>`);
  expect(JSON.stringify(obs)).not.toMatch(/privatePassword|privateQuery|privateFragment/);
  expect(JSON.stringify(obs)).not.toContain(token);
  expect(obs.text).toContain('[token]');
});

test('an aria-disabled composed ancestor disables descendant controls', () => {
  const obs = observe('<div><button>Open</button></div>');
  document.querySelector('div')!.setAttribute('aria-disabled', 'true');
  expect(execute(click(obs.revision), document, { verified: true }).note).toMatch(/^stale target:/);
  expect(snapshot(document, { geometry: false }).elements).toEqual([]);
});

test.each(['long suffix', 'redacted collision'])('local semantics reject %s changes beyond uploaded context', (change) => {
  const name = change === 'long suffix' ? 'Project '.repeat(40) + 'Alpha' : 'owner@alpha.test';
  const obs = observe(`<main aria-label="Projects"><ul><li><span>${name}</span><button>Edit</button></li></ul></main>`);
  document.querySelector('span')!.textContent = change === 'long suffix' ? 'Project '.repeat(40) + 'Beta' : 'owner@beta.test';
  expect(execute(click(obs.revision), document, { verified: true }).note).toMatch(/^stale target:/);
});

test.each(['hidden', 'inert'])('open shadow controls respect a %s host at capture and dispatch', (attribute) => {
  document.body.innerHTML = '<x-project></x-project>';
  const host = document.querySelector('x-project')!;
  host.attachShadow({ mode: 'open' }).innerHTML = '<button>Open</button>';
  const obs = snapshot(document, { geometry: false });
  host.setAttribute(attribute, '');
  expect(execute(click(obs.revision), document, { verified: true }).note).toMatch(/^stale target:/);
  expect(snapshot(document, { geometry: false }).elements).toEqual([]);
});

test('disabled fieldsets are unavailable except controls in their first legend', () => {
  const obs = observe('<fieldset><legend><button>Help</button></legend><button>Open</button></fieldset>');
  (document.querySelector('fieldset') as HTMLFieldSetElement).disabled = true;
  expect(execute(click(obs.revision, 2), document, { verified: true }).note).toMatch(/^stale target:/);
  expect(snapshot(document, { geometry: false }).elements.map(e => e.text)).toEqual(['Help']);
});

test.each(['scroll', 'focus'])('a dialog appearing on %s blocks the final click or typed value', (trigger) => {
  const obs = observe(trigger === 'focus' ? '<input aria-label="Name">' : '<button>Open</button>');
  const el = document.querySelector('button,input') as HTMLElement;
  const overlay = () => document.body.insertAdjacentHTML('beforeend', '<div role="dialog" aria-modal="true"><button>Close</button></div>');
  if (trigger === 'scroll') el.scrollIntoView = overlay;
  else el.addEventListener('focus', overlay);
  let pressed = 0;
  el.addEventListener('click', () => pressed++);
  const result = execute({ ...click(obs.revision), action: trigger === 'focus' ? 'type' : 'click', text: 'private value' }, document, { verified: true });
  expect(result.note).toMatch(/^stale target:/);
  expect(pressed).toBe(0);
  expect((el as HTMLInputElement).value ?? '').toBe('');
});

test('a dialog appearing while confirmation is pending blocks the approved send', () => {
  const obs = observe('<form><button>Send message</button></form>');
  expect(execute(click(obs.revision), document, { verified: true, dryRun: true }).confirm).toBe('send');
  document.body.insertAdjacentHTML('beforeend', '<div role="dialog" aria-modal="true"><button>Close</button></div>');
  expect(execute(click(obs.revision), document, { verified: true, confirmed: true }).note).toMatch(/^stale target:/);
});

test('context and control coverage are bounded and disclose omissions', () => {
  const obs = observe('<main aria-label="Projects">' + Array.from({ length: 830 }, (_, i) => `<li>${'project description '.repeat(20)}${i}<button>Edit</button></li>`).join('') + '</main>');
  expect(obs.elements).toHaveLength(120);
  expect(obs.elements.reduce((n, e) => n + (e.region?.length ?? 0) + (e.row?.length ?? 0), 0)).toBeLessThanOrEqual(6000);
  expect(obs.context_truncated).toBe(true);
  expect(obs.elements_truncated).toBe(true);
  expect(obs.candidate_limit_reached).toBe(true);
  expect(obs.omitted_elements).toBeGreaterThanOrEqual(680);
}, 60_000); // This includes parsing the 830-control fixture in jsdom, which has no native layout engine.

test('a changed checkbox state cannot reverse a choice captured in the observation', () => {
  const obs = observe('<label><input type="checkbox">Agree</label>');
  const input = document.querySelector('input')!;
  input.checked = true;
  expect(execute(click(obs.revision), document, { verified: true }).note).toMatch(/^stale target:/);
  expect(input.checked).toBe(true);
});

test('missing revision and a previous snapshot revision cannot dispatch a target', () => {
  const first = observe('<button>Open details</button>');
  let pressed = 0;
  document.querySelector('button')!.addEventListener('click', () => pressed++);
  expect(execute(click(), document, { verified: true }).note).toMatch(/^stale target:/);
  snapshot(document, { geometry: false });
  expect(execute(click(first.revision), document, { verified: true }).note).toMatch(/^stale target:/);
  expect(pressed).toBe(0);
});

test.each(['replacement', 'label', 'parent', 'href', 'form', 'disabled', 'hidden', 'aria-hidden', 'inert'])('changed %s refuses execution even if the page copies the target attribute', (change) => {
  const obs = observe('<main><form id="one"></form><form id="two"></form><div id="row">Alpha<a href="/alpha">Edit</a></div><div id="other">Beta</div></main>');
  const target = document.querySelector('a')!;
  let pressed = 0;
  document.addEventListener('click', count, { once: true });
  function count() { pressed++; }
  if (change === 'replacement') target.replaceWith(target.cloneNode(true));
  if (change === 'label') target.textContent = 'Delete';
  if (change === 'parent') document.getElementById('other')!.append(target);
  if (change === 'href') target.setAttribute('href', '/beta');
  if (change === 'form') target.setAttribute('form', 'two');
  if (change === 'disabled') target.setAttribute('aria-disabled', 'true');
  if (change === 'hidden') target.hidden = true;
  if (change === 'aria-hidden') target.parentElement!.setAttribute('aria-hidden', 'true');
  if (change === 'inert') target.parentElement!.setAttribute('inert', '');
  expect(execute(click(obs.revision), document, { verified: true }).note).toMatch(/^stale target:/);
  expect(pressed).toBe(0);
  document.removeEventListener('click', count);
});

test('a changed row label invalidates the same surviving Edit node', () => {
  const obs = observe('<table><tr><td id="name">Alpha</td><td><button>Edit</button></td></tr></table>');
  document.getElementById('name')!.textContent = 'Beta';
  expect(execute(click(obs.revision), document, { verified: true }).note).toMatch(/^stale target:/);
});

test('changing the base URL invalidates the resolved link destination', () => {
  const base = document.createElement('base');
  base.href = 'https://fixture.test/alpha/';
  document.head.append(base);
  try {
    const obs = observe('<a href="details">Open</a>');
    base.href = 'https://fixture.test/beta/';
    expect(execute(click(obs.revision), document, { verified: true }).note).toMatch(/^stale target:/);
  } finally { base.remove(); }
});

test('confirmation cannot authorize a changed form owner', () => {
  const obs = observe('<form id="one"></form><form id="two"></form><button type="submit" form="one">Send message</button>');
  expect(execute(click(obs.revision), document, { verified: true, dryRun: true }).confirm).toBe('send');
  document.querySelector('button')!.setAttribute('form', 'two');
  expect(execute(click(obs.revision), document, { verified: true, confirmed: true }).note).toMatch(/^stale target:/);
});

test('open shadow-root targets use captured references and scoped labels', () => {
  document.body.innerHTML = '<x-project></x-project>';
  const root = document.querySelector('x-project')!.attachShadow({ mode: 'open' });
  root.innerHTML = '<section aria-label="Alpha"><span id="name">Row Alpha</span><button aria-labelledby="name">Edit</button></section>';
  const obs = snapshot(document, { geometry: false });
  expect(obs.elements[0]!.text).toBe('Row Alpha');
  expect(obs.elements[0]!.region).toBe('section: Alpha');
  let pressed = 0;
  root.querySelector('button')!.addEventListener('click', () => pressed++);
  expect(execute(click(obs.revision), document, { verified: true }).ok).toBe(true);
  root.querySelector('button')!.replaceWith(root.querySelector('button')!.cloneNode(true));
  expect(execute(click(obs.revision), document, { verified: true }).note).toMatch(/^stale target:/);
  expect(pressed).toBe(1);
});
