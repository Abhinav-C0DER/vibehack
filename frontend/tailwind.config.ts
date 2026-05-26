const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
    // This is the safety net:
    "./*.{js,ts,jsx,tsx,mdx}", 
  ],
  theme: {
    extend: {
      colors: {
        void: "#0A0A0A",
        ghost: {
          white: "#F8F8F8",
          cyan: "#00FFFF",
          lime: "#39FF14",
          border: "rgba(255, 255, 255, 0.1)",
        },
      },
      backgroundImage: {
        "spectral-gradient": "linear-gradient(to right, #00FFFF, #39FF14)",
      },
    },
  },
  plugins: [],
};
export default config;
