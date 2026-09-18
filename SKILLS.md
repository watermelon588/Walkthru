# Skills

Which agent skill to load for which job in this repo. Skills live in `~/.claude/skills/` (index: `my-skills`). Load with the Skill tool or `/<name>`.

## By phase
| Work | Skill |
|---|---|
| Starting a session, choosing a workflow | `using-agent-skills` |
| New feature with no spec | `spec-driven-development`, then `planning-and-task-breakdown` |
| Vague idea or product decision | `idea-refine`, `interview-me` |
| High-stakes decision (auth, payments, agent safety) | `doubt-driven-development` |
| Implementing a task | `incremental-implementation`, `test-driven-development` |
| Framework or API usage you are unsure of | `source-driven-development` |
| API endpoints, module contracts | `api-and-interface-design` |
| Something broke | `debugging-and-error-recovery` |
| Review before merge | `code-review-and-quality`, `ponytail-review` (over-engineering) |
| Auth, uploads, webhooks, PII masking | `security-and-hardening` |
| Logging, metrics, traces | `observability-and-instrumentation` |
| Commits, branches, releases | `git-workflow-and-versioning` |
| CI pipelines | `ci-cd-and-automation` |
| Launch checklist | `shipping-and-launch` |

## UI
| Work | Skill |
|---|---|
| Any page or component | `frontend-ui-engineering` + [DESIGN.md](DESIGN.md) |
| Landing or marketing sections | `design-taste-frontend` |
| UX critique, polish, audit | `impeccable` |
| GSAP in React | `gsap-react`, `gsap-scrolltrigger`, `gsap-performance` |
| Motion details, component feel | `emil-design-eng` |

## AI and agents
| Work | Skill |
|---|---|
| Claude API calls, model choice, pricing, caching, evals | `claude-api` (subcommands: `build-eval`, `cost-optimize`) |
| LangGraph / LangSmith | No dedicated skill. Use `source-driven-development` against the official LangGraph docs. |

## Always on
`ponytail` (simplest working solution) runs by default through hooks.
