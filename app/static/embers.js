(() => {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const canvas = document.createElement("canvas");
  canvas.className = "embers";
  document.body.prepend(canvas);
  const ctx = canvas.getContext("2d");

  const scheme = matchMedia("(prefers-color-scheme: dark)");
  let w, h, dpr, sprite, cfg, parts = [], last = 0;

  const CONFIG = {
    dark:  { rgb: [255, 150, 60], count: 55, speed: [18, 46], size: [0.8, 2.4], alpha: 0.9,  blend: "lighter" },
    light: { rgb: [176, 124, 44], count: 26, speed: [6, 16],  size: [1.0, 2.6], alpha: 0.38, blend: "source-over" },
  };

  function makeSprite(rgb) {
    const s = document.createElement("canvas");
    s.width = s.height = 64;
    const c = s.getContext("2d");
    const g = c.createRadialGradient(32, 32, 0, 32, 32, 32);
    g.addColorStop(0, "rgba(255,245,220,1)");
    g.addColorStop(0.18, `rgba(${rgb},0.95)`);
    g.addColorStop(0.5, `rgba(${rgb},0.25)`);
    g.addColorStop(1, `rgba(${rgb},0)`);
    c.fillStyle = g;
    c.fillRect(0, 0, 64, 64);
    return s;
  }

  const rand = (a, b) => a + Math.random() * (b - a);

  function spawn(p, initial) {
    p.x = rand(0, w);
    p.y = initial ? rand(0, h) : h + rand(10, 60);
    p.size = rand(...cfg.size);
    p.vy = rand(...cfg.speed);
    p.wind = rand(-6, 10);
    p.amp = rand(6, 26);
    p.freq = rand(0.4, 1.3);
    p.phase = rand(0, Math.PI * 2);
    p.flick = rand(0, Math.PI * 2);
    p.flickSpeed = rand(3, 9);
    p.maxLife = rand(7, 16);
    p.life = initial ? rand(0, p.maxLife) : 0;
    p.baseX = p.x;
  }

  function setup() {
    cfg = scheme.matches ? CONFIG.dark : CONFIG.light;
    sprite = makeSprite(cfg.rgb);
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = innerWidth;
    h = innerHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.round(cfg.count * Math.min(1, (w * h) / 900000 + 0.4));
    parts = Array.from({ length: count }, () => {
      const p = {};
      spawn(p, true);
      return p;
    });
  }

  function frame(t) {
    const dt = Math.min((t - last) / 1000, 0.05);
    last = t;
    ctx.clearRect(0, 0, w, h);
    ctx.globalCompositeOperation = cfg.blend;

    for (const p of parts) {
      p.life += dt;
      p.y -= p.vy * dt;
      p.baseX += p.wind * dt;
      p.x = p.baseX + Math.sin(p.life * p.freq + p.phase) * p.amp;
      p.flick += p.flickSpeed * dt;

      const f = p.life / p.maxLife;
      if (f >= 1 || p.y < -30) { spawn(p, false); continue; }

      const fade = Math.pow(Math.sin(Math.PI * f), 0.8);
      const flicker = 0.7 + 0.3 * Math.sin(p.flick) * Math.sin(p.flick * 0.37 + 1);
      const shrink = cfg === CONFIG.dark ? 1 - 0.45 * f : 1;
      const s = p.size * 9 * shrink;

      ctx.globalAlpha = cfg.alpha * fade * flicker;
      ctx.drawImage(sprite, p.x - s / 2, p.y - s / 2, s, s);
    }
    ctx.globalAlpha = 1;
    requestAnimationFrame(frame);
  }

  function start() {
    setup();
    last = performance.now();
    requestAnimationFrame(frame);
  }

  let resizeTimer;
  addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(setup, 150);
  });
  scheme.addEventListener("change", setup);

  start();
})();