import { useEffect, useRef, useState } from "react";
import { getPlan, getSession, WEB_URL, type GoalPlan, type PlanSummary } from "../../lib/api";
import type { AgentState } from "../../lib/agent-bird";
import { AgentStatus } from "./AgentStatus";
import { suggestGoals } from "../../lib/goals";
import { runTest, snapshotActiveTab, type Progress, type RunOptions } from "./run";

const PERSONAS = [
  ["first_timer", "First-time visitor"],
  ["phone_user", "Phone user"],
  ["buyer", "Small-business buyer"],
  ["skeptic", "Skeptical developer"],
] as const;

const STATUS_COPY: Record<string, string> = {
  done: "Reached the goal.",
  gave_up: "Gave up before reaching the goal.",
  budget: "Ran out of steps before reaching the goal.",
  stuck: "Kept trying the same thing and got stuck.",
  captcha: "Stopped at a CAPTCHA.",
  stopped: "Ended early. A partial report is being prepared.",
  safe_stop: "Everything worked up to the send button. Walkthru only sends on verified domains, after you approve.",
  looping: "Walkthru stopped the test user for going in circles. That is Walkthru's limit, not a problem with your site.",
};

export function App() {
  const [site, setSite] = useState<string>("");
  const [goal, setGoal] = useState("Sign up for an account");
  const [persona, setPersona] = useState<(typeof PERSONAS)[number][0]>("first_timer");
  const [loggedIn, setLoggedIn] = useState(false);
  const [progress, setProgress] = useState<Progress>({ phase: "idle", steps: [] });
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const [plan, setPlan] = useState<PlanSummary | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [understood, setUnderstood] = useState<GoalPlan | null>(null);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    if (typeof chrome === "undefined" || !chrome.tabs) return; // previewing outside the extension
    chrome.tabs.query({ active: true, currentWindow: true }).then(([tab]) => setSite(tab?.url ?? ""));
    getSession().then((s) => setSignedIn(!!s));
    const onChange = (changes: Record<string, chrome.storage.StorageChange>) => {
      if ("session" in changes) setSignedIn(!!changes.session.newValue);
    };
    chrome.storage.onChanged.addListener(onChange);
    return () => chrome.storage.onChanged.removeListener(onChange);
  }, []);

  // The server decides the plan; refresh it when the account connects and after every run.
  const finished = progress.phase === "finished" || progress.phase === "error";
  useEffect(() => {
    if (signedIn) getPlan().then(setPlan).catch(() => setPlan(null));
    else setPlan(null);
  }, [signedIn, finished]);
  const canLogIn = plan?.logged_in ?? false;

  // Goals this page can actually support, read from its links and buttons (like "Sign up" or "Pricing").
  useEffect(() => {
    if (!/^https?:\/\//.test(site)) {
      setSuggestions([]);
      return;
    }
    snapshotActiveTab().then((obs) => setSuggestions(obs ? suggestGoals(obs.elements) : []));
  }, [site]);

  const running = progress.phase === "running" || progress.phase === "starting";
  const outOfRuns = plan?.runs_left === 0;
  const canStart = /^https?:\/\//.test(site) && goal.trim().length > 0 && !running && signedIn === true && !outOfRuns;
  // Say why Start is disabled instead of leaving a dead button.
  const blocked = running || canStart
    ? null
    : signedIn === false
      ? "Connect your account to start."
      : !/^https?:\/\//.test(site)
        ? "Open a website in this tab to test it."
        : !goal.trim()
          ? "Give the test user a goal."
          : outOfRuns
            ? `No test runs left ${plan?.plan === "free" ? "this month" : "in this pass"}. Instant Scans stay free.`
            : null;
  const agentState: AgentState = progress.phase === "error"
    ? "stopped"
    : progress.phase === "finished"
      ? progress.status === "done" || progress.status === "safe_stop" ? "complete" : "stopped"
      : running
        ? "observing"
        : "ready";
  const agentActivity = progress.phase === "starting"
    ? "Reading the page"
    : progress.phase === "running"
      ? `Testing step ${Math.max(1, progress.steps.length)}`
      : progress.phase === "finished"
        ? STATUS_COPY[progress.status ?? ""] ?? "Run finished"
        : progress.phase === "error"
          ? "The run needs attention"
          : "Ready to test this tab";

  async function start(e: React.FormEvent) {
    e.preventDefault();
    if (!canStart) return;
    abort.current = new AbortController();
    setUnderstood(null);
    const opts: RunOptions = { site, goal: goal.trim(), persona, logged_in: loggedIn && canLogIn, max_steps: plan?.max_steps ?? 12, signal: abort.current.signal };
    await runTest(opts, (p) => {
      if (p.plan) setUnderstood(p.plan);
      setProgress(p);
    });
  }

  return (
    <main className="panel">
      <header className="brand">
        <div>
          <h1>Walkthru</h1>
          <span>See where strangers get stuck.</span>
        </div>
        <AgentStatus activity={agentActivity} state={agentState} />
      </header>

      {signedIn === false && (
        <p className="notice" role="status">
          Not connected. <a href={`${WEB_URL}/app`} target="_blank" rel="noreferrer">Sign in to Walkthru</a> and click "Connect extension".
        </p>
      )}

      <form onSubmit={start} aria-busy={running}>
        <label>
          Site under test
          <span className="site">{site || "Open the site in this tab first"}</span>
        </label>
        <label htmlFor="goal">
          Goal for the test user
          <textarea id="goal" value={goal} onChange={(e) => setGoal(e.target.value)} disabled={running} required />
        </label>
        {suggestions.length > 0 && !running && (
          <div className="suggestions" role="group" aria-label="Goals this page supports">
            {suggestions.map((s) => (
              <button key={s} type="button" className="chip" aria-pressed={goal === s} onClick={() => setGoal(s)}>{s}</button>
            ))}
          </div>
        )}
        <label htmlFor="persona">
          Test user
          <select id="persona" value={persona} onChange={(e) => setPersona(e.target.value as typeof persona)} disabled={running}>
            {PERSONAS.map(([v, l]) => {
              const included = !plan || plan.personas.includes(v);
              return <option key={v} value={v} disabled={!included}>{included ? l : `${l} (paid plans)`}</option>;
            })}
          </select>
        </label>
        <label className="row" htmlFor="logged">
          <input id="logged" type="checkbox" checked={loggedIn && canLogIn} onChange={(e) => setLoggedIn(e.target.checked)} disabled={running || !canLogIn} />
          This is a logged-in page (safe mode: no destructive clicks, confirm before submits)
        </label>
        {plan && !canLogIn && <p className="hint">Logged-in pages need a paid plan. Free runs test public pages.</p>}
        {plan && (
          <p className="hint" role="status">
            {plan.runs_left} of {plan.runs_allowed} test runs left {plan.plan === "free" ? "this month" : "in your pass"}, up to {plan.max_steps} steps each.
          </p>
        )}
        <p className="hint">Sends redacted text snapshots and saves up to 8 evidence frames, deleted after 30 days. Form values are masked before capture.</p>
        <div className="actions">
          <button type="submit" className="primary" disabled={!canStart}>{running ? "Testing…" : "Start test"}</button>
          {running && <button type="button" onClick={() => abort.current?.abort()}>Stop</button>}
        </div>
        {blocked && <p className="hint" role="status">{blocked}</p>}
      </form>

      {understood && (
        <section className="notice" aria-label="How Walkthru understood the goal">
          <p>Understood as: {understood.intent}</p>
          <ol className="checklist">
            {understood.checkpoints.map((c) => <li key={c}>{c}</li>)}
          </ol>
        </section>
      )}

      {progress.phase === "error" && <p className="error">{progress.message}</p>}
      {progress.evidenceWarning && <p className="notice" role="status">{progress.evidenceWarning}</p>}

      {progress.phase === "finished" && (
        <section className="summary" aria-label="Result">
          <h2>{STATUS_COPY[progress.status ?? ""]}</h2>
          <p>{progress.steps.length} steps. Highest confusion: {Math.max(0, ...progress.steps.map((s) => s.confusion))} of 3.</p>
          {progress.status === "safe_stop" && (
            <p>
              <a href={`${WEB_URL}/docs#verify`} target="_blank" rel="noreferrer">Verify your domain</a> to let the test user send once, after you approve.
            </p>
          )}
          {progress.runId && (
            <p>
              <a href={`${WEB_URL}/app/runs/${progress.runId}`} target="_blank" rel="noreferrer">View the full report</a> (ready in about half a minute)
            </p>
          )}
        </section>
      )}

      <section aria-label="Think-aloud log">
        {progress.steps.length === 0 ? (
          <p className="empty">{progress.phase === "idle" ? "The test user's thoughts will appear here." : "Waiting for the first step…"}</p>
        ) : (
          <ol className="steps">
            {progress.steps.map((s, i) => (
              <li key={i} className="step">
                <span className="n">{i + 1}</span>
                <div>
                  <p className="thought">{s.thought}</p>
                  <span className="act">
                    {s.action}{s.target_id != null ? ` #${s.target_id}` : ""}{s.text ? " (value hidden)" : ""}
                    {s.confusion >= 2 && <span className="conf">confused</span>}
                  </span>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      <footer className="panel-footer">
        <a href={`${WEB_URL}/app`} target="_blank" rel="noreferrer">Dashboard</a>
        <a href={`${WEB_URL}/docs#run-a-test`} target="_blank" rel="noreferrer">Help</a>
        <a href={`${WEB_URL}/privacy`} target="_blank" rel="noreferrer">Privacy</a>
      </footer>
    </main>
  );
}
