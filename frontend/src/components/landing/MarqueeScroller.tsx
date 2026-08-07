'use client';

interface LogoItem {
  name: string;
  svgUrl: string;
  gradientClass: string;
}

const LOGOS: LogoItem[] = [
  { name: 'Procure', svgUrl: 'https://svgl.app/library/procure.svg', gradientClass: 'from-blue-500 to-indigo-600' },
  { name: 'Shopify', svgUrl: 'https://svgl.app/library/shopify.svg', gradientClass: 'from-emerald-400 to-amber-500' },
  { name: 'Blender', svgUrl: 'https://svgl.app/library/blender.svg', gradientClass: 'from-orange-500 to-blue-600' },
  { name: 'Figma', svgUrl: 'https://svgl.app/library/figma.svg', gradientClass: 'from-purple-500 to-rose-500' },
  { name: 'Spotify', svgUrl: 'https://svgl.app/library/spotify.svg', gradientClass: 'from-emerald-500 to-teal-400' },
  { name: 'Lottielab', svgUrl: 'https://svgl.app/library/lottielab.svg', gradientClass: 'from-yellow-400 to-emerald-500' },
  { name: 'Google Cloud', svgUrl: 'https://svgl.app/library/google-cloud.svg', gradientClass: 'from-sky-400 to-blue-600' },
  { name: 'Bing', svgUrl: 'https://svgl.app/library/bing.svg', gradientClass: 'from-cyan-400 to-teal-600' },
];

export default function MarqueeScroller() {
  return (
    <div className="w-full max-w-[1400px] mx-auto mt-10 overflow-hidden marquee-mask py-4 relative">
      <style>{`
        @keyframes continuousMarquee {
          0% {
            transform: translateX(0%);
          }
          100% {
            transform: translateX(-50%);
          }
        }
        .marquee-track-inner {
          display: flex;
          width: max-content;
          gap: 1.5rem;
          animation: continuousMarquee 20s linear infinite;
        }
        .marquee-track-inner:hover {
          animation-play-state: paused;
        }
      `}</style>

      <div className="marquee-track-inner">
        {/* Render list twice to ensure infinite seamless loop */}
        {[...LOGOS, ...LOGOS].map((logo, index) => (
          <div
            key={`${logo.name}-${index}`}
            className="group relative h-24 w-40 shrink-0 flex items-center justify-center rounded-full bg-white border border-slate-200/60 shadow-sm hover:border-slate-300 transition-all overflow-hidden cursor-pointer"
          >
            {/* Hover Hex Gradient Background */}
            <div
              className={`absolute inset-0 bg-gradient-to-r ${logo.gradientClass} opacity-0 scale-150 group-hover:opacity-100 group-hover:scale-100 transition-all duration-500 ease-out pointer-events-none`}
            />

            {/* Logo Image */}
            <img
              src={logo.svgUrl}
              alt={logo.name}
              className="h-8 w-auto relative z-10 object-contain transition-all duration-300 group-hover:brightness-0 group-hover:invert"
              loading="lazy"
            />
          </div>
        ))}
      </div>
    </div>
  );
}

