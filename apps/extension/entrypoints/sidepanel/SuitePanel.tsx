import { useEffect, useState } from "react";
import { WEB_URL } from "../../lib/api";
import { coverage, deleteSuite, loadRun, loadSuites, matches, MAX_SCENARIOS, nextIndex, origin, saveSuite, type Scenario, type Suite, type SuiteRun } from "../../lib/suite";

type Draft = Omit<Scenario, "id" | "name">;

/** R-S14: saved suites for the site in this tab. Running one is the parent's job (it owns the browser and quotes). */
export function SuitePanel({ site, connection, disabled, draft, live, handoff, onRun, onHandoff }: {
  site: string; connection: string | undefined; disabled: boolean; draft: () => Draft | null;
  live: SuiteRun | null; handoff: Scenario | null;
  onRun: (suite: Suite, resume: SuiteRun | null) => void; onHandoff: (ok: boolean) => void;
}) {
  const [suites, setSuites] = useState<Suite[]>([]);
  const [saved, setSaved] = useState<SuiteRun | null>(null);
  const [target, setTarget] = useState("new");
  const [suiteName, setSuiteName] = useState("");
  const [scenarioName, setScenarioName] = useState("");
  const [note, setNote] = useState<string | null>(null);
  const here = /^https?:\/\//.test(site) ? origin(site) : null;

  useEffect(() => {
    loadSuites().then(setSuites).catch(() => setSuites([]));
    if (connection) loadRun(connection).then(setSaved).catch(() => setSaved(null));
    else setSaved(null);
  }, [connection, live]);

  if (!here) return null;
  const mine = suites.filter((s) => s.origin === here);
  const progress = live ?? saved;

  async function add() {
    const d = draft();
    if (!d) { setNote("Open the site and give the test user a goal first."); return; }
    const existing = mine.find((s) => s.id === target);
    const scenario: Scenario = { ...d, id: crypto.randomUUID(), name: scenarioName.trim() || d.goal.slice(0, 60) };
    const suite: Suite = existing ? { ...existing, scenarios: [...existing.scenarios, scenario] }
      : { id: crypto.randomUUID(), name: suiteName.trim(), origin: here!, scenarios: [scenario] };
    try {
      setSuites(await saveSuite(suite));
      setTarget(suite.id);
      setScenarioName("");
      setNote(`Saved "${scenario.name}" in ${suite.name}.`);
    } catch (error) {
      setNote(error instanceof Error ? error.message : "Could not save the scenario.");
    }
  }

  async function remove(suite: Suite, id?: string) {
    const left = id ? suite.scenarios.filter((s) => s.id !== id) : [];
    setSuites(left.length ? await saveSuite({ ...suite, scenarios: left }) : await deleteSuite(suite.id));
  }

  const current = progress ? mine.find((s) => matches(s, progress)) : undefined;
  const cov = current && progress ? coverage(current, progress) : null;
  const left = current && progress ? progress.results.filter((r) => (r.state === "pending" || (r.state === "not_tested" && r.resumable))).length : 0;

  return (
    <section className="suites" aria-labelledby="suites-title">
      <h2 id="suites-title">Saved suites</h2>
      <p className="hint">A suite runs up to {MAX_SCENARIOS} saved scenarios one after another in this browser. Each uses one run, with its own terms and step cap. It covers only these scenarios, not your whole app. Saved in this browser only.</p>

      {handoff && (
        <div className="handoff" role="alert">
          <p>{handoff.name} uses signed-in pages. Sign in to the site in this tab yourself, then continue. Walkthru never signs in for you.</p>
          <div className="actions">
            <button type="button" className="primary" onClick={() => onHandoff(true)}>I am signed in, continue</button>
            <button type="button" onClick={() => onHandoff(false)}>Not now</button>
          </div>
        </div>
      )}

      {mine.length === 0 ? <p className="empty">No suites for this site yet.</p> : (
        <ul className="suite-list">
          {mine.map((s) => {
            const resumable = matches(s, progress) && nextIndex(progress) !== -1;
            return (
              <li key={s.id}>
                <details>
                  <summary>{s.name} ({s.scenarios.length} {s.scenarios.length === 1 ? "scenario" : "scenarios"})</summary>
                  <ol>
                    {s.scenarios.map((x) => (
                      <li key={x.id}>
                        <span>{x.name}: {x.goal} ({x.max_steps} steps{x.logged_in ? ", signed in" : ""}{x.assertion ? ", count check" : ""})</span>
                        <button type="button" className="link" disabled={disabled} onClick={() => void remove(s, x.id)} aria-label={`Remove ${x.name}`}>Remove</button>
                      </li>
                    ))}
                  </ol>
                </details>
                <div className="actions">
                  <button type="button" disabled={disabled} onClick={() => onRun(s, null)}>Run suite</button>
                  {resumable && <button type="button" disabled={disabled} onClick={() => onRun(s, progress)}>Resume ({left} left)</button>}
                  <button type="button" className="link" disabled={disabled} onClick={() => void remove(s)}>Delete suite</button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <fieldset className="suite-add" disabled={disabled}>
        <legend>Save this setup as a scenario</legend>
        <label htmlFor="scenario-name">Scenario name<input id="scenario-name" type="text" value={scenarioName} onChange={(e) => setScenarioName(e.target.value)} maxLength={80} placeholder="Defaults to the goal" /></label>
        <label htmlFor="suite-target">Add to
          <select id="suite-target" value={target} onChange={(e) => setTarget(e.target.value)}>
            <option value="new">A new suite</option>
            {mine.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </label>
        {target === "new" && <label htmlFor="suite-name">New suite name<input id="suite-name" type="text" value={suiteName} onChange={(e) => setSuiteName(e.target.value)} maxLength={80} required /></label>}
        <button type="button" onClick={() => void add()}>Save scenario</button>
        {note && <p className="hint" role="status">{note}</p>}
      </fieldset>

      {cov && current && (
        <div className="coverage" aria-label={`Coverage for ${current.name}`}>
          <h3>Coverage: {current.name}</h3>
          {([["Tested", cov.tested], ["Blocked", cov.blocked], ["Not tested", cov.not_tested]] as const).map(([label, items]) => (
            <div key={label}>
              <h4>{label} ({items.length})</h4>
              {items.length > 0 && <ul>{items.map((x) => (
                <li key={x.name}>{x.name}{x.reason ? `: ${x.reason}` : ""} {x.run_id && <a href={`${WEB_URL}/app/runs/${x.run_id}`} target="_blank" rel="noreferrer">Report</a>}</li>
              ))}</ul>}
            </div>
          ))}
          {cov.promised.length > 0 && <div><h4>Declared checks ({cov.promised.length})</h4><ul>{cov.promised.map((p) => <li key={p.name}>{p.name}: {p.check}. {p.run_id ? <>Verdict in <a href={`${WEB_URL}/app/runs/${p.run_id}`} target="_blank" rel="noreferrer">its report</a>.</> : "Not run yet."}</li>)}</ul></div>}
          <div>
            <h4>Pages visited ({cov.routes.length})</h4>
            <p className="hint">Found along the way. Visiting a page is not a promise it was checked.</p>
            {cov.routes.length > 0 && <ul className="routes">{cov.routes.map((r) => <li key={r}>{r}</li>)}</ul>}
          </div>
        </div>
      )}
    </section>
  );
}
