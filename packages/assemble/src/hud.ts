// The control pill at the bottom of the screen. Plain DOM inside the component's shadow root.

export interface HudActions {
  tour(on: boolean): void
  speed(n: number): void
  close(): void
  replay(): void
  sound(on: boolean): void
}

export interface HudState {
  agents: number
  /** colour and initial of the first few agents, for the avatar stack */
  faces: [string, string][]
  built: number
  total: number
  /** nothing left in view: ask the visitor to scroll */
  idle: boolean
}

// Press feedback and the entrance only move transform and opacity; hover is gated to real pointers.
const CSS = `
.hud{position:fixed;left:50%;bottom:20px;transform:translateX(-50%);display:flex;align-items:center;gap:10px;
  max-width:calc(100vw - 32px);box-sizing:border-box;padding:6px 6px 6px 12px;border-radius:12px;pointer-events:auto;
  background:#1c1c1f;color:#f4f4f5;font:500 12px/1 system-ui,-apple-system,"Segoe UI",sans-serif;white-space:nowrap;
  box-shadow:0 8px 28px rgba(0,0,0,.28),0 0 0 1px rgba(255,255,255,.06);font-variant-numeric:tabular-nums;
  transition:opacity .2s cubic-bezier(.23,1,.32,1),transform .2s cubic-bezier(.23,1,.32,1)}
@starting-style{.hud{opacity:0;transform:translateX(-50%) translateY(8px)}}
.faces{display:flex}
.faces i{width:18px;height:18px;margin-left:-5px;border-radius:50%;box-shadow:0 0 0 1.5px #1c1c1f;display:grid;place-items:center;
  font:600 9px/1 system-ui,sans-serif;font-style:normal;color:#fff}
.faces i:first-child{margin-left:0}
.dim{color:#a1a1aa;font-weight:400}
.sep{width:1px;height:14px;background:rgba(255,255,255,.14)}
.bar{width:56px;height:3px;border-radius:2px;background:rgba(255,255,255,.14);overflow:hidden}
.bar b{display:block;height:100%;background:#f4f4f5;transform-origin:left;transform:scaleX(0);transition:transform .2s linear}
button{all:unset;box-sizing:border-box;min-width:28px;height:28px;padding:0 9px;border-radius:7px;text-align:center;cursor:pointer;
  font:inherit;color:inherit;transition:transform .12s cubic-bezier(.23,1,.32,1),background-color .15s ease}
button:active{transform:scale(.96)}
button:focus-visible{outline:2px solid #f4f4f5;outline-offset:1px}
button[aria-pressed=true],button.primary{background:#f4f4f5;color:#1c1c1f}
@media (hover:hover) and (pointer:fine){button:hover{background:rgba(255,255,255,.12)}button[aria-pressed=true]:hover,button.primary:hover{background:#fff}}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
@media (max-width:520px){.faces,.bar,.sep{display:none}}
@media (prefers-reduced-motion:reduce){.hud,button,.bar b{transition:none}}
`

export class Hud {
  el = document.createElement('div')
  style = document.createElement('style')
  act: HudActions
  key = ''
  speed: number
  noun: string

  constructor(root: ShadowRoot, act: HudActions, tour: boolean, speed: number, noun: string, sound: boolean) {
    this.act = act
    this.speed = speed
    this.noun = noun
    this.style.textContent = CSS
    this.el.className = 'hud'
    this.el.setAttribute('role', 'toolbar')
    this.el.setAttribute('aria-label', 'Page rebuild')
    this.el.innerHTML =
      '<span class="sr" role="status">Rebuilding page</span><span class="faces"></span>' +
      '<span><span data-k="agents">0</span> <span class="dim" data-k="noun"></span></span><span class="sep"></span>' +
      '<span data-k="count"></span><span class="bar"><b></b></span>' +
      '<button data-k="tour" type="button">Tour</button><button data-k="speed" type="button"></button><button data-k="sound" type="button">Sound</button>' +
      '<button data-k="close" type="button" aria-label="Skip rebuild">✕</button>'
    this.q('noun').textContent = noun
    const soundBtn = this.q('sound')
    soundBtn.setAttribute('aria-pressed', String(sound))
    soundBtn.onclick = () => {
      const on = soundBtn.getAttribute('aria-pressed') !== 'true'
      soundBtn.setAttribute('aria-pressed', String(on))
      act.sound(on)
    }
    const tourBtn = this.q('tour')
    tourBtn.setAttribute('aria-pressed', String(tour))
    tourBtn.onclick = () => {
      const on = tourBtn.getAttribute('aria-pressed') !== 'true'
      tourBtn.setAttribute('aria-pressed', String(on))
      act.tour(on)
    }
    const speedBtn = this.q('speed')
    const label = () => {
      speedBtn.textContent = this.speed + '×'
      speedBtn.setAttribute('aria-label', `Speed ${this.speed} times, change`)
    }
    label()
    speedBtn.onclick = () => {
      this.speed = (this.speed % 3) + 1
      label()
      act.speed(this.speed)
    }
    this.q('close').onclick = () => act.close()
    root.append(this.style, this.el)
  }

  private q(k: string) {
    return this.el.querySelector(`[data-k="${k}"]`) as HTMLElement
  }

  update(s: HudState) {
    const key = [s.agents, s.built, s.total, s.idle, s.faces.join()].join()
    if (key === this.key) return
    this.key = key
    this.q('agents').textContent = String(s.agents)
    const count = this.q('count')
    count.textContent = s.idle ? 'scroll to keep building' : `${s.built} `
    if (!s.idle) {
      const dim = document.createElement('span')
      dim.className = 'dim'
      dim.textContent = `/ ${s.total} layers`
      count.append(dim)
    }
    ;(this.el.querySelector('.bar b') as HTMLElement).style.transform = `scaleX(${s.total ? s.built / s.total : 0})`
    const faces = this.el.querySelector('.faces')!
    faces.replaceChildren(
      ...s.faces.map(([color, initial]) => {
        const i = document.createElement('i')
        i.style.background = color
        i.textContent = initial
        return i
      }),
    )
  }

  /** end state: what happened, Replay, Done */
  finish(agents: number, seconds: number) {
    const text = `Rebuilt by ${agents} ${this.noun} in ${seconds.toFixed(1)}s`
    this.el.innerHTML = '<span class="sr" role="status">Page rebuilt</span><span data-k="sum"></span><button data-k="replay" type="button">Replay</button><button data-k="close" class="primary" type="button">Done</button>'
    this.q('sum').textContent = text
    this.q('replay').onclick = () => this.act.replay()
    this.q('close').onclick = () => this.act.close()
  }
}
