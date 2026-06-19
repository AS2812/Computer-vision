import { useEffect, useState } from "react";
import { Leaf, ArrowRight } from "lucide-react";
import type { Lang } from "../appTypes";

interface LeafSplashProps {
  lang: Lang;
  onComplete: () => void;
}

export function LeafSplash({ lang, onComplete }: LeafSplashProps) {
  const [phase, setPhase] = useState<"grow" | "zoom" | "fade">("grow");

  useEffect(() => {
    // Phase 1: Grow & Float (0s to 2.2s)
    // Phase 2: Zoom/Enter inside (2.2s to 3.8s)
    // Phase 3: Fade out entire splash (3.8s to 4.5s)
    const zoomTimeout = setTimeout(() => {
      setPhase("zoom");
    }, 2200);

    const fadeTimeout = setTimeout(() => {
      setPhase("fade");
    }, 3800);

    const completeTimeout = setTimeout(() => {
      onComplete();
    }, 4500);

    return () => {
      clearTimeout(zoomTimeout);
      clearTimeout(fadeTimeout);
      clearTimeout(completeTimeout);
    };
  }, [onComplete]);

  const isAr = lang === "ar";

  return (
    <div
      className={`fixed inset-0 z-[9999] flex flex-col items-center justify-center overflow-hidden transition-opacity duration-700 bg-[#020e0a] ${
        phase === "fade" ? "opacity-0 pointer-events-none" : "opacity-100"
      }`}
    >
      {/* 3D Immersive background grid of cells */}
      <div className="absolute inset-0 opacity-20 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_#0b3020_0%,_transparent_70%)]" />
        <div
          className={`absolute inset-0 grid grid-cols-8 grid-rows-8 gap-4 p-8 transition-transform duration-[3000ms] ease-in-out ${
            phase === "zoom" ? "scale-[4] rotate(12deg) opacity-40" : "scale-100"
          }`}
        >
          {Array.from({ length: 64 }).map((_, i) => (
            <div
              key={i}
              className="border border-emerald-500/10 rounded-lg bg-emerald-500/[0.02] shadow-[inset_0_0_8px_rgba(52,211,153,0.05)] animate-pulse"
              style={{ animationDelay: `${(i % 5) * 0.4}s` }}
            />
          ))}
        </div>
      </div>

      {/* Floating glowing spores / chloroplasts */}
      <div className="absolute inset-0 pointer-events-none">
        {Array.from({ length: 25 }).map((_, i) => {
          const size = Math.random() * 8 + 4;
          const left = Math.random() * 100;
          const top = Math.random() * 100;
          const duration = Math.random() * 6 + 4;
          const delay = Math.random() * 2;
          return (
            <div
              key={i}
              className={`absolute rounded-full bg-emerald-400/40 blur-[1px] transition-transform duration-[2000ms] ${
                phase === "zoom" ? "scale-[6] opacity-0 translate-y-[-100px]" : ""
              }`}
              style={{
                width: `${size}px`,
                height: `${size}px`,
                left: `${left}%`,
                top: `${top}%`,
                animation: `floatSpore ${duration}s ease-in-out infinite`,
                animationDelay: `${delay}s`,
                boxShadow: "0 0 10px #34d399",
              }}
            />
          );
        })}
      </div>

      {/* Main 3D Leaf Element */}
      <div
        className={`relative flex items-center justify-center transition-all ease-in-out ${
          phase === "grow"
            ? "scale-100 rotate-0 opacity-100 duration-1000"
            : phase === "zoom"
            ? "scale-[25] rotate-[45deg] opacity-0 duration-[2000ms]"
            : "scale-[30] opacity-0 duration-500"
        }`}
        style={{
          transformStyle: "preserve-3d",
          perspective: "1000px",
        }}
      >
        {/* Soft backlighting */}
        <div className="absolute w-64 h-64 bg-emerald-500/20 rounded-full blur-[80px] animate-pulse" />

        {/* 3D Leaf SVG wrapper */}
        <svg
          width="240"
          height="280"
          viewBox="0 0 200 240"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="relative filter drop-shadow-[0_10px_35px_rgba(52,211,153,0.3)] animate-[swayLeaf_6s_ease-in-out_infinite]"
        >
          <defs>
            <linearGradient id="leafGrad" x1="100" y1="0" x2="100" y2="240" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#cff45b" />
              <stop offset="60%" stopColor="#67dd8e" />
              <stop offset="100%" stopColor="#0a3c26" />
            </linearGradient>
            <linearGradient id="veinGrad" x1="100" y1="0" x2="100" y2="240" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.8" />
              <stop offset="50%" stopColor="#cff45b" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#67dd8e" stopOpacity="0.2" />
            </linearGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Leaf Body */}
          <path
            d="M 100 20 
               C 135 45, 175 90, 165 140 
               C 155 190, 120 210, 100 230 
               C 80 210, 45 190, 35 140 
               C 25 90, 65 45, 100 20 Z"
            fill="url(#leafGrad)"
          />

          {/* Main Stem */}
          <path
            d="M 100 20 L 100 235"
            stroke="url(#veinGrad)"
            strokeWidth="3.5"
            strokeLinecap="round"
            className="animate-[drawVein_2s_ease-out_both]"
          />

          {/* Branching Veins (Left side) */}
          <path d="M 100 60 Q 75 45 50 65" stroke="url(#veinGrad)" strokeWidth="2.5" strokeLinecap="round" />
          <path d="M 100 95 Q 70 80 40 110" stroke="url(#veinGrad)" strokeWidth="2.5" strokeLinecap="round" />
          <path d="M 100 135 Q 65 125 42 160" stroke="url(#veinGrad)" strokeWidth="2.2" strokeLinecap="round" />
          <path d="M 100 175 Q 75 170 55 198" stroke="url(#veinGrad)" strokeWidth="1.8" strokeLinecap="round" />

          {/* Branching Veins (Right side) */}
          <path d="M 100 60 Q 125 45 150 65" stroke="url(#veinGrad)" strokeWidth="2.5" strokeLinecap="round" />
          <path d="M 100 95 Q 130 80 160 110" stroke="url(#veinGrad)" strokeWidth="2.5" strokeLinecap="round" />
          <path d="M 100 135 Q 135 125 158 160" stroke="url(#veinGrad)" strokeWidth="2.2" strokeLinecap="round" />
          <path d="M 100 175 Q 125 170 145 198" stroke="url(#veinGrad)" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      </div>

      {/* Typography Overlay */}
      <div
        className={`absolute bottom-16 left-4 right-4 text-center max-w-lg mx-auto transition-all duration-700 ${
          phase === "zoom" || phase === "fade" ? "opacity-0 translate-y-[20px]" : "opacity-100 translate-y-0"
        }`}
      >
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-400/10 text-emerald-300 border border-emerald-400/25 mb-4 shadow-[0_0_15px_rgba(52,211,153,0.2)]">
          <Leaf size={24} className="animate-spin" style={{ animationDuration: "12s" }} />
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-emerald-50 mb-2 sm:text-4xl">
          {isAr ? "أجروفيجن مصر" : "AgroVision Egypt"}
        </h1>
        <p className="text-sm font-semibold text-emerald-300/80 mb-1">
          {isAr ? "الدخول إلى تفاصيل الورقة..." : "Entering the leaf..."}
        </p>
        <p className="text-xs text-emerald-200/50 leading-relaxed px-4">
          {isAr
            ? "ذكاء نباتي ثلاثي الأبعاد لفحص أوراق الطماطم فورياً على جهازك دون مشاركة موقعك."
            : "On-device 3D tomato leaf screening. Secure, instant, and private."}
        </p>
      </div>

      {/* Skip Button */}
      <button
        onClick={onComplete}
        className={`absolute top-6 right-6 z-[10000] flex items-center gap-1.5 rounded-full border border-white/10 bg-black/40 px-4 py-2 text-xs font-semibold text-emerald-200 backdrop-blur hover:bg-black/60 hover:border-emerald-400/40 transition-all ${
          phase === "fade" ? "opacity-0 pointer-events-none" : "opacity-100"
        }`}
      >
        {isAr ? "تخطي العرض" : "Skip Intro"}{" "}
        <ArrowRight size={14} className={isAr ? "rotate-180" : ""} />
      </button>

      {/* Additional inline CSS to guarantee keyframes execute correctly */}
      <style>{`
        @keyframes floatSpore {
          0%, 100% {
            transform: translateY(0) translateX(0);
          }
          50% {
            transform: translateY(-20px) translateX(10px);
          }
        }
        @keyframes swayLeaf {
          0%, 100% {
            transform: rotateY(0deg) rotateX(0deg) translateY(0);
          }
          50% {
            transform: rotateY(15deg) rotateX(5deg) translateY(-8px);
          }
        }
        @keyframes drawVein {
          from {
            stroke-dasharray: 220;
            stroke-dashoffset: 220;
          }
          to {
            stroke-dasharray: 220;
            stroke-dashoffset: 0;
          }
        }
      `}</style>
    </div>
  );
}
