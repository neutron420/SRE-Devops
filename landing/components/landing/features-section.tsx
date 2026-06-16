"use client";

import { useEffect, useRef, useState } from "react";

const features = [
  {
    number: "01",
    title: "Multi-Tenant SaaS",
    description: "Allows different Discord servers (guilds) to securely register their own independent clusters. Each server's settings, endpoints, and credentials are completely isolated.",
    stats: { value: "100%", label: "tenant isolation" },
  },
  {
    number: "02",
    title: "AES-256 Cryptography",
    description: "Kubernetes configs uploaded via Discord are encrypted using Fernet symmetric authenticated cryptography before being saved in a database, ensuring credentials are secure at rest.",
    stats: { value: "256-bit", label: "symmetric encryption" },
  },
  {
    number: "03",
    title: "Agentic Diagnostics",
    description: "A stateful LangGraph multi-agent workflow powered by Gemini 2.5 analyzes container status, stdout logs, and metrics anomalies to produce action-oriented recommendations.",
    stats: { value: "Gemini 2.5", label: "agentic reasoning model" },
  },
  {
    number: "04",
    title: "Proactive Monitoring",
    description: "A background loop watches pod health. Transitioning to unhealthy states (e.g., OOMKilled, CrashLoopBackOff) alerts designated channels, clearing once resolved.",
    stats: { value: "24/7/365", label: "continuous cluster monitoring" },
  },
];

// Floating dot particles visualization
function ParticleVisualization() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameRef = useRef(0);
  const mouseRef = useRef({ x: 0.5, y: 0.5 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };
    resize();
    window.addEventListener("resize", resize);

    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouseRef.current = {
        x: (e.clientX - rect.left) / rect.width,
        y: (e.clientY - rect.top) / rect.height,
      };
    };
    canvas.addEventListener("mousemove", handleMouseMove);

    // Generate stable particle positions
    const COUNT = 30; // Reduced to keep performance smooth across multiple cards
    const particles = Array.from({ length: COUNT }, (_, i) => {
      const seed = i * 1.618;
      return {
        bx: ((seed * 127.1) % 1),
        by: ((seed * 311.7) % 1),
        phase: seed * Math.PI * 2,
        speed: 0.4 + (seed % 0.4),
        radius: 1.2 + (seed % 2.2),
      };
    });

    let time = 0;
    const render = () => {
      const rect = canvas.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;

      ctx.clearRect(0, 0, w, h);

      const mx = mouseRef.current.x;
      const my = mouseRef.current.y;

      particles.forEach((p) => {
        const flowX = Math.sin(time * p.speed * 0.4 + p.phase) * 15;
        const flowY = Math.cos(time * p.speed * 0.3 + p.phase * 0.7) * 10;

        const bx = p.bx * w;
        const by = p.by * h;
        const dx = p.bx - mx;
        const dy = p.by - my;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const influence = Math.max(0, 1 - dist * 2.8);

        const x = bx + flowX + influence * Math.cos(time + p.phase) * 15;
        const y = by + flowY + influence * Math.sin(time + p.phase) * 15;

        const pulse = Math.sin(time * p.speed + p.phase) * 0.5 + 0.5;
        const alpha = 0.04 + pulse * 0.08 + influence * 0.15;

        ctx.beginPath();
        ctx.arc(x, y, p.radius + pulse * 0.8, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
        ctx.fill();
      });

      time += 0.016;
      frameRef.current = requestAnimationFrame(render);
    };
    render();

    return () => {
      window.removeEventListener("resize", resize);
      canvas.removeEventListener("mousemove", handleMouseMove);
      cancelAnimationFrame(frameRef.current);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-auto"
      style={{ width: "100%", height: "100%" }}
    />
  );
}

export function FeaturesSection() {
  const [isVisible, setIsVisible] = useState(false);
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsVisible(true);
      },
      { threshold: 0.1 }
    );

    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section
      id="features"
      ref={sectionRef}
      className="relative py-24 lg:py-32 overflow-hidden"
    >
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
        {/* Header - Full width with diagonal layout */}
        <div className="relative mb-24 lg:mb-32">
          <div className="grid lg:grid-cols-12 gap-8 items-end">
            <div className="lg:col-span-7">
              <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-6">
                <span className="w-12 h-px bg-foreground/30" />
                Features
              </span>
              <h2
                className={`text-6xl md:text-7xl lg:text-[128px] font-display tracking-tight leading-[0.9] transition-all duration-1000 ${
                  isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
                }`}
              >
                Intelligent
                <br />
                <span className="text-muted-foreground">SRE operations.</span>
              </h2>
            </div>
            <div className="lg:col-span-5 lg:pb-4">
              <p className={`text-xl text-muted-foreground leading-relaxed transition-all duration-1000 delay-200 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
              }`}>
                Invite the SRE Copilot to your Discord server to secure credentials, diagnose container failures, and query metrics anomaly traces.
              </p>
            </div>
          </div>
        </div>

        {/* Bento Grid Layout */}
        <div className="grid md:grid-cols-2 gap-4 lg:gap-6">
          {features.map((feature, index) => (
            <div 
              key={feature.number}
              className={`relative bg-black border border-foreground/10 min-h-[380px] overflow-hidden group transition-all duration-700 flex flex-col justify-between p-8 lg:p-10 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-12"
              }`}
              style={{ transitionDelay: `${index * 100}ms` }}
            >
              <ParticleVisualization />
              <div className="relative z-10">
                <span className="font-mono text-xs text-[#eca8d6]">{feature.number}</span>
                <h3 className="text-2xl lg:text-3xl font-display mt-3 mb-4 group-hover:translate-x-2 transition-transform duration-500 text-white">
                  {feature.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed mb-6 max-w-md">
                  {feature.description}
                </p>
              </div>
              <div className="relative z-10 mt-auto pt-4 border-t border-white/5">
                <span className="text-3xl lg:text-4xl font-display text-white">{feature.stats.value}</span>
                <span className="block text-xs text-muted-foreground font-mono mt-1">{feature.stats.label}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
