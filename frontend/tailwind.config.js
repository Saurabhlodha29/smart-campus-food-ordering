/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          bg:        "#0E0801",
          surface:   "#1C1108",
          card:      "#2A1A0A",
          primary:   "#FF6500",
          primaryhv: "#CC5200",
          accent:    "#FFB347",
          text1:     "#FFFFFF",
          text2:     "#C8A87E",
          text3:     "#7A6045",
          border:    "rgba(255,101,0,0.18)",
          glass:     "rgba(255,255,255,0.06)",
          success:   "#22C55E",
          warning:   "#F59E0B",
          error:     "#EF4444",
        }
      },
      fontFamily: {
        poppins: ["Poppins", "sans-serif"],
      },
      borderRadius: {
        "2xl": "16px",
        "3xl": "24px",
        "4xl": "32px",
      },
      boxShadow: {
        card:   "0 4px 24px rgba(0,0,0,0.4)",
        orange: "0 4px 20px rgba(255,101,0,0.35)",
        glass:  "0 8px 32px rgba(0,0,0,0.3)",
      },
    },
  },
  plugins: [],
};
