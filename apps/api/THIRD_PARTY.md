# Third-party notices

## geo-optimizer-skill

The GEO signal taxonomy in `app/scans/geo.py` and `app/scans/geo_depth.py` is adapted from [geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill). No code package is installed from that project. Its license is MIT.

Copyright (c) 2026 Juan Camilo Auriti

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## SEO depth check references

The rule inventory in `app/scans/seo_depth.py` was reviewed against these MIT projects. The implementation is original and uses Google Search Central's current rules for specific findings:

- [Open SEO Crawler](https://github.com/puneetindersingh/open-seo-crawler/blob/master/LICENSE): Copyright (c) 2026 Puneet Inder Singh.
- [LibreCrawl](https://github.com/PhialsBasement/LibreCrawl/blob/main/LICENSE): Copyright (c) 2025 Phiality.
- [FreeCrawl SEO Tool](https://github.com/kemalai/FreeCrawl-SEO-Tool/blob/main/LICENSE): Copyright (c) 2026 Kemal Acar.

Their MIT permission notice and disclaimer:

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Security parity data and rules (P1.2)

These projects supply the rules and data behind `app/scans/csp.py`, `app/scans/libraries.py`, `app/scans/secrets.py`
and `app/scans/takeover.py`. The data files live in `app/scans/data/` and are refreshed with
`scripts/refresh_security_data.py`, which keeps only the fields Walkthru uses and converts gitleaks' Go regular
expressions to Python. No package from these projects is installed.

- **retire.js** (`app/scans/data/retire.json`, derived from `repository/jsrepository-v4.json`):
  [RetireJS/retire.js](https://github.com/RetireJS/retire.js), Apache License 2.0. Changes: fields reduced to
  extractors, vulnerable version ranges, severities, CVE and GHSA ids and summaries.
- **gitleaks** (`app/scans/data/gitleaks.json`, derived from `config/gitleaks.toml`):
  [gitleaks/gitleaks](https://github.com/gitleaks/gitleaks), MIT License, Copyright (c) 2019 Zachary Rice. Changes:
  regular expressions rewritten from RE2 to Python syntax; the generic and JWT rules are left out.
- **csp-evaluator** (checks ported in `app/scans/csp.py`, no files copied): [google/csp-evaluator](https://github.com/google/csp-evaluator),
  Copyright 2016 Google Inc., Apache License 2.0. Changes: a subset of the security checks, rewritten in Python, with
  Walkthru's own severities and wording.
- **can-i-take-over-xyz** (`app/scans/data/takeover.json`, derived from `fingerprints.json`):
  [EdOverflow/can-i-take-over-xyz](https://github.com/EdOverflow/can-i-take-over-xyz), by EdOverflow and contributors,
  licensed under [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).
  Changes: reduced to services marked vulnerable; status-code-only fingerprints removed.
- **MDN HTTP Observatory** ([mdn/mdn-http-observatory](https://github.com/mdn/mdn-http-observatory), MPL-2.0): the
  header tests (HSTS thresholds, cookie prefixes, SRI, CORS) informed Walkthru's own Python code. No files were copied.

Apache License 2.0 (retire.js, csp-evaluator): you may obtain a copy at http://www.apache.org/licenses/LICENSE-2.0.
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

gitleaks MIT License: the MIT permission notice and disclaimer are reproduced in full above and apply to the gitleaks
rules with Copyright (c) 2019 Zachary Rice.
