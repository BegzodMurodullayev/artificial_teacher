/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ── Dark Space Palette ──────────────────────────────
        "space-black":  "#05050a",
        "space-deep":   "#080b14",
        "space-dark":   "#0d1117",
        "space-card":   "#0f1420",
        "space-border": "#1a2035",
        "space-muted":  "#1e2a45",

        // ── Neon Accents ────────────────────────────────────
        "neon-cyan":    "#00f3ff",
        "neon-cyan-dim":"#00a8b5",
        "neon-purple":  "#bc13fe",
        "neon-purple-dim":"#8209b3",
        "neon-pink":    "#ff2d78",
        "neon-green":   "#00ff88",
        "neon-yellow":  "#ffe600",

        // ── Text ────────────────────────────────────────────
        "text-primary":   "#e8eaf0",
        "text-secondary": "#8892aa",
        "text-muted":     "#4a5568",
      },

      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },

      fontSize: {
        "2xs": ["0.65rem", { lineHeight: "1rem" }],
      },

      boxShadow: {
        // Neon glow effects
        "neon-cyan":    "0 0 8px #00f3ff, 0 0 24px #00f3ff55, 0 0 48px #00f3ff22",
        "neon-purple":  "0 0 8px #bc13fe, 0 0 24px #bc13fe55, 0 0 48px #bc13fe22",
        "neon-pink":    "0 0 8px #ff2d78, 0 0 24px #ff2d7855, 0 0 48px #ff2d7822",
        "neon-green":   "0 0 8px #00ff88, 0 0 24px #00ff8855",
        "neon-sm-cyan": "0 0 4px #00f3ff, 0 0 12px #00f3ff44",
        "neon-sm-purple":"0 0 4px #bc13fe, 0 0 12px #bc13fe44",
        "glass":        "0 8px 32px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255,255,255,0.05)",
        "card":         "0 4px 24px rgba(0, 0, 0, 0.4)",
        "card-hover":   "0 8px 40px rgba(0, 0, 0, 0.6)",
        "inner-glow":   "inset 0 0 24px rgba(0, 243, 255, 0.06)",
      },

      backgroundImage: {
        // Gradients
        "grad-cyan-purple": "linear-gradient(135deg, #00f3ff 0%, #bc13fe 100%)",
        "grad-purple-pink": "linear-gradient(135deg, #bc13fe 0%, #ff2d78 100%)",
        "grad-space":       "linear-gradient(180deg, #05050a 0%, #080b14 50%, #0d1117 100%)",
        "grad-card":        "linear-gradient(145deg, rgba(15,20,32,0.9) 0%, rgba(8,11,20,0.95) 100%)",
        "grad-glow-cyan":   "radial-gradient(ellipse at center, rgba(0,243,255,0.15) 0%, transparent 70%)",
        "grad-glow-purple": "radial-gradient(ellipse at center, rgba(188,19,254,0.15) 0%, transparent 70%)",
        "shimmer":          "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.05) 50%, transparent 100%)",
      },

      backdropBlur: {
        xs: "2px",
      },

      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
        "4xl": "2rem",
      },

      animation: {
        "glow-pulse":     "glowPulse 2s ease-in-out infinite",
        "float":          "float 6s ease-in-out infinite",
        "shimmer":        "shimmer 2.5s linear infinite",
        "spin-slow":      "spin 8s linear infinite",
        "fade-up":        "fadeUp 0.4s ease-out",
        "scale-in":       "scaleIn 0.3s ease-out",
        "slide-up":       "slideUp 0.5s cubic-bezier(0.16,1,0.3,1)",
        "slide-right":    "slideRight 0.4s cubic-bezier(0.16,1,0.3,1)",
      },

      keyframes: {
        glowPulse: {
          "0%, 100%": { boxShadow: "0 0 8px #00f3ff, 0 0 24px #00f3ff55" },
          "50%":      { boxShadow: "0 0 16px #00f3ff, 0 0 48px #00f3ff88, 0 0 80px #00f3ff33" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%":      { transform: "translateY(-8px)" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        fadeUp: {
          "0%":   { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        scaleIn: {
          "0%":   { opacity: "0", transform: "scale(0.92)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        slideUp: {
          "0%":   { opacity: "0", transform: "translateY(24px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideRight: {
          "0%":   { opacity: "0", transform: "translateX(-16px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
      },

      transitionTimingFunction: {
        "spring": "cubic-bezier(0.16, 1, 0.3, 1)",
      },
    },
  },
  plugins: [],
}
