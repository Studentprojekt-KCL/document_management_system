import { useEffect, useRef, useState } from "preact/hooks";

interface Props { birdSrc?: string; pipeSrc?: string }

export default function FlappyBird({ birdSrc = "/bird.png", pipeSrc = "/pipe.png" }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [score, setScore] = useState(0);

  useEffect(() => {
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    const W = canvas.width, H = canvas.height;
    const GAP = 160, PIPE_W = 60;
    const bird = new Image(); bird.src = birdSrc;
    const pipe = new Image(); pipe.src = pipeSrc;
    let y = H / 2, v = 0, pipes: { x: number; gap: number; passed?: boolean }[] = [{ x: W, gap: 200 }];
    let alive = true, s = 0, frame = 0;

    const jump = (e: KeyboardEvent | MouseEvent) => {
      if ("code" in e && e.code !== "Space") return;
      if ("code" in e) e.preventDefault();
      if (!alive) { y = H / 2; v = 0; pipes = [{ x: W, gap: 200 }]; s = 0; setScore(0); alive = true; return; }
      v = -7;
    };
    addEventListener("keydown", jump); canvas.addEventListener("click", jump);

    let raf = 0;
    const loop = () => {
      ctx.fillStyle = "#70c5ce"; ctx.fillRect(0, 0, W, H);
      if (alive) { v += 0.4; y += v; frame++; if (frame % 90 === 0) pipes.push({ x: W, gap: 80 + Math.random() * (H - GAP - 160) }); }
      for (const p of pipes) {
        if (alive) p.x -= 2;
        ctx.drawImage(pipe, p.x, 0, PIPE_W, p.gap);
        const bottomY = p.gap + GAP;
        ctx.save();
        ctx.translate(p.x + PIPE_W / 2, bottomY + (H - bottomY) / 2);
        ctx.scale(1, -1);
        ctx.drawImage(pipe, -PIPE_W / 2, -(H - bottomY) / 2, PIPE_W, H - bottomY);
        ctx.restore();
        if (alive && p.x < 60 && p.x + PIPE_W > 50 && (y < p.gap || y > p.gap + GAP)) alive = false;
        if (alive && !p.passed && p.x + PIPE_W < 50) { p.passed = true; s++; setScore(s); }
      }
      pipes = pipes.filter((p) => p.x > -PIPE_W);
      ctx.drawImage(bird, 50, y - 15, 40, 30);
      if (y > H || y < 0) alive = false;
      if (!alive) { ctx.fillStyle = "#fff"; ctx.font = "30px sans-serif"; ctx.fillText("Click to restart", W / 2 - 110, H / 2); }
      raf = requestAnimationFrame(loop);
    };
    loop();
    return () => { cancelAnimationFrame(raf); removeEventListener("keydown", jump); };
  }, []);

  return (
    <div class="flex flex-col items-center">
      <h2 class="text-xl font-bold mb-2">Score: {score}</h2>
      <canvas ref={canvasRef} width={400} height={500} style={{ border: "1px solid #333" }} />
    </div>
  );
}
