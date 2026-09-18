import { useEffect, useRef, useState } from "react";
import { runTest, type Progress, type RunOptions } from "./run";

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
  aborted: "Stopped.",
};

export function App() {
  const [site, setSite] = useState<string>("");
  const [goal, setGoal] = useState("Sign up for an account");
  const [persona, setPersona] = useState<(typeof PERSONAS)[number][0]>("first_timer");
  const [loggedIn, setLoggedIn] = useState(false);
  const [progress, setProgress] = useState<Progress>({ phase: "idle", steps: [] });
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    if (typeof chrome === "undefined" || !chrome.tabs) return; // previewing outside the extension
    chrome.tabs.query({ active: true, currentWindow: true }).then(([tab]) => setSite(tab?.url ?? ""));
  }, []);

  const running = progress.phase === "running" || progress.phase === "starting";
  const canStart = /^https?:\/\//.test(site) && goal.trim().length > 0 && !running;

  async function start(e: React.FormEvent) {
    e.preventDefault();
    if (!canStart) return;
    abort.current = new AbortController();
    const opts: RunOptions = { site, goal: goal.trim(), persona, logged_in: loggedIn, max_steps: 12, signal: abort.current.signal };
    await runTest(opts, setProgress);
  }

  return (
    <main className="panel">
      <header className="brand">
        <h1>Walkthru</h1>
        <span>See where strangers get stuck.</span>
      </header>

      <form onSubmit={start} aria-busy={running}>
        <label>
          Site under test
          <span className="site">{site || "Open the site in this tab first"}</span>
        </label>
        <label htmlFor="goal">
          Goal for the test user
          <textarea id="goal" value={goal} onChange={(e) => setGoal(e.target.value)} disabled={running} required />
        </label>
        <label htmlFor="persona">
          Test user
          <select id="persona" value={persona} onChange={(e) => setPersona(e.target.value as typeof persona)} disabled={running}>
            {PERSONAS.map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </label>
        <label className="row" htmlFor="logged">
          <input id="logged" type="checkbox" checked={loggedIn} onChange={(e) => setLoggedIn(e.target.checked)} disabled={running} />
          This is a logged-in page (safe mode: no destructive clicks, confirm before submits)
        </label>
        <p className="hint">Sends a text snapshot of each page. Emails, long numbers and typed values are masked first.</p>
        <div className="actions">
          <button type="submit" className="primary" disabled={!canStart}>{running ? "Testing…" : "Start test"}</button>
          {running && <button type="button" onClick={() => abort.current?.abort()}>Stop</button>}
        </div>
      </form>

      {progress.phase !== "idle" && (
        <div className="status" role="status">
          <span className={`dot${running ? " live" : ""}`} aria-hidden="true" />
          {progress.phase === "starting" && "Reading the page…"}
          {progress.phase === "running" && `Step ${progress.steps.length}: ${progress.message ?? "thinking"}`}
          {progress.phase === "finished" && STATUS_COPY[progress.status ?? ""]}
          {progress.phase === "error" && "Something went wrong."}
        </div>
      )}
      {progress.phase === "error" && <p className="error">{progress.message}</p>}

      {progress.phase === "finished" && (
        <section className="summary" aria-label="Result">
          <h2>{STATUS_COPY[progress.status ?? ""]}</h2>
          <p>{progress.steps.length} steps. Highest confusion: {Math.max(0, ...progress.steps.map((s) => s.confusion))} of 3.</p>
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
                    {s.action}{s.target_id != null ? ` #${s.target_id}` : ""}{s.text ? ` "${s.text}"` : ""}
                    {s.confusion >= 2 && <span className="conf">confused</span>}
                  </span>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </main>
  );
}
