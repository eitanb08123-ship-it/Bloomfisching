(function () {
  const canvas = document.getElementById('sphere');
  const ctx = canvas.getContext('2d');

  const POINT_COUNT = 900;
  const RADIUS = 220;

  let points = [];
  let angleY = 0;
  let angleX = 0;
  let activity = 0.15; // 0 = idle, 1 = thinking/speaking hard
  let hueBase = 190; // cyan; switches to red (~355) in serious mode

  // Even distribution on a sphere via the golden-spiral method.
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < POINT_COUNT; i++) {
    const y = 1 - (i / (POINT_COUNT - 1)) * 2;
    const radiusAtY = Math.sqrt(1 - y * y);
    const theta = goldenAngle * i;
    points.push({
      x: Math.cos(theta) * radiusAtY,
      y: y,
      z: Math.sin(theta) * radiusAtY,
    });
  }

  function project(p, cx, cy, scale) {
    const x1 = p.x * Math.cos(angleY) - p.z * Math.sin(angleY);
    const z1 = p.x * Math.sin(angleY) + p.z * Math.cos(angleY);
    const y2 = p.y * Math.cos(angleX) - z1 * Math.sin(angleX);
    const z2 = p.y * Math.sin(angleX) + z1 * Math.cos(angleX);

    const perspective = 500 / (500 + z2 * RADIUS);
    return {
      x: cx + x1 * RADIUS * perspective * scale,
      y: cy + y2 * RADIUS * perspective * scale,
      depth: z2,
    };
  }

  function draw() {
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h / 2;
    const scale = 1 + activity * 0.08;

    const projected = points.map((p) => project(p, cx, cy, scale));
    projected.sort((a, b) => a.depth - b.depth);

    for (const p of projected) {
      const brightness = (p.depth + 1) / 2; // 0..1
      const size = 0.6 + brightness * 1.8 + activity * 1.2;
      const alpha = 0.25 + brightness * 0.65;
      const hue = hueBase + activity * 15;
      ctx.beginPath();
      ctx.fillStyle = `hsla(${hue}, 95%, ${55 + brightness * 20}%, ${alpha})`;
      ctx.shadowColor = `hsla(${hue}, 100%, 70%, ${alpha})`;
      ctx.shadowBlur = 4 + brightness * 6;
      ctx.arc(p.x, p.y, size, 0, Math.PI * 2);
      ctx.fill();
    }

    const baseSpeed = 0.0022;
    angleY += baseSpeed + activity * 0.006;
    angleX += (baseSpeed * 0.4) + activity * 0.002;

    requestAnimationFrame(draw);
  }

  requestAnimationFrame(draw);

  window.JarvisSphere = {
    setActivity(level) {
      activity = Math.max(0, Math.min(1, level));
    },
    setTheme(name) {
      hueBase = name === 'serious' ? 355 : 190;
    },
  };
})();
