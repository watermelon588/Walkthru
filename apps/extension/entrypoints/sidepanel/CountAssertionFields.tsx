import type { FilterCountAssertion } from '../../lib/api';

export function CountAssertionFields({ enabled, onEnable, value, onChange, disabled }: {
  enabled: boolean; onEnable: (v: boolean) => void; value: FilterCountAssertion; onChange: (v: FilterCountAssertion) => void; disabled: boolean;
}) {
  return <fieldset className="count-assertion" disabled={disabled}>
    <legend>Optional outcome check</legend>
    <label className="row" htmlFor="count-enabled"><input id="count-enabled" type="checkbox" checked={enabled} onChange={(e) => onEnable(e.target.checked)} />Check a synthetic filtered count</label>
    {enabled && <>
      <p className="hint">This run checks the declared filter state on your verified site. Sign in to the site yourself first if needed. Use synthetic data. Missing or stale expectations produce an inconclusive result.</p>
      <label htmlFor="count-path">Dashboard path<input type="text" id="count-path" value={value.path} onChange={(e) => onChange({ ...value, path: e.target.value })} required pattern="/[A-Za-z0-9/_.-]*" maxLength={200} /></label>
      <label htmlFor="count-filter">Filter value<input type="text" id="count-filter" value={value.filter_value} onChange={(e) => onChange({ ...value, filter_value: e.target.value })} required pattern="[A-Za-z0-9 _.-]+" maxLength={80} /></label>
      <label htmlFor="count-label">Visible count label<input type="text" id="count-label" value={value.count_label} onChange={(e) => onChange({ ...value, count_label: e.target.value })} required pattern="[A-Za-z][A-Za-z0-9 _-]*" maxLength={80} /></label>
      <label htmlFor="count-expected">Expected count<input id="count-expected" type="number" min={0} max={100000} step={1} value={value.expected_count ?? ''} onChange={(e) => onChange({ ...value, expected_count: e.target.value === '' ? null : e.target.valueAsNumber })} /></label>
      <label htmlFor="count-dataset">Synthetic dataset ID<input type="text" id="count-dataset" value={value.dataset_id ?? ''} onChange={(e) => onChange({ ...value, dataset_id: e.target.value || null })} pattern="[A-Za-z0-9_.-]+" maxLength={80} /></label>
      <label htmlFor="count-time">Dataset timestamp, including timezone<input type="text" id="count-time" value={value.dataset_at ?? ''} onChange={(e) => onChange({ ...value, dataset_at: e.target.value || null })} placeholder="2026-10-06T04:00:00Z" maxLength={40} /></label>
      <label htmlFor="count-age">Maximum dataset age, seconds<input id="count-age" type="number" min={1} max={86400} step={1} value={value.max_age_seconds} onChange={(e) => onChange({ ...value, max_age_seconds: e.target.valueAsNumber })} required /></label>
      <label htmlFor="count-tolerance">Count tolerance, records<input id="count-tolerance" type="number" min={0} max={100} step={1} value={value.tolerance} onChange={(e) => onChange({ ...value, tolerance: e.target.valueAsNumber })} required /></label>
      <p className="hint">The page must show Filter: {value.filter_value}, {value.count_label}: a count, Dataset: its ID and Dataset time: its timestamp. This visible UI check does not certify backend access or persistence.</p>
    </>}
  </fieldset>;
}
