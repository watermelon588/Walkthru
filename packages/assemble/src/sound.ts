// Optional sound, synthesised with Web Audio: no audio files. Created only after a user gesture (the HUD button),
// because browsers keep an AudioContext silent until then.

export class Sound {
  ctx = new AudioContext()
  out = this.ctx.createGain()
  lastKey = 0

  constructor() {
    this.out.gain.value = 0.5
    this.out.connect(this.ctx.destination)
    void this.ctx.resume()
  }

  // one short tone that slides from `from` to `to` Hz and fades out, placed left or right by where it happened
  private blip(from: number, to: number, seconds: number, volume: number, x: number, type: OscillatorType = 'sine') {
    const t = this.ctx.currentTime
    const osc = this.ctx.createOscillator()
    const gain = this.ctx.createGain()
    const pan = this.ctx.createStereoPanner()
    osc.type = type
    osc.frequency.setValueAtTime(from, t)
    osc.frequency.exponentialRampToValueAtTime(Math.max(1, to), t + seconds)
    gain.gain.setValueAtTime(volume, t)
    gain.gain.exponentialRampToValueAtTime(0.0001, t + seconds)
    pan.pan.value = Math.max(-1, Math.min(1, (x / innerWidth) * 2 - 1)) * 0.7
    osc.connect(gain).connect(pan).connect(this.out)
    osc.start(t)
    osc.stop(t + seconds + 0.02)
  }

  /** a keystroke; several typists at once are thinned out so it stays a patter, not a buzz */
  key(x: number) {
    const now = this.ctx.currentTime
    if (now - this.lastKey < 0.045) return
    this.lastKey = now
    this.blip(1500 + Math.random() * 700, 800, 0.03, 0.045, x, 'triangle')
  }

  /** a box, picture or copy landing */
  place(x: number) {
    this.blip(170, 68, 0.13, 0.28, x)
  }

  /** a pen stroke finishing */
  stroke(x: number) {
    this.blip(760, 520, 0.08, 0.06, x)
  }

  /** the page is whole again */
  done() {
    this.blip(523.25, 523.25, 0.9, 0.11, innerWidth / 2)
    this.blip(783.99, 783.99, 1.1, 0.09, innerWidth / 2)
  }

  close() {
    void this.ctx.close()
  }
}
