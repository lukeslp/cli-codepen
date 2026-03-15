const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const t = Date.now() / 1000;
  for (let i = 0; i < 20; i++) {
    const x = canvas.width / 2 + Math.cos(t + i * 0.3) * (50 + i * 5);
    const y = canvas.height / 2 + Math.sin(t + i * 0.3) * (50 + i * 5);
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fillStyle = `hsl(${i * 18 + t * 50}, 80%, 60%)`;
    ctx.fill();
  }
  requestAnimationFrame(draw);
}
draw();
