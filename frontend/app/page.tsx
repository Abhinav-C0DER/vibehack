"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Ghost, ShieldCheck, Zap, Sparkles, AlertTriangle } from "lucide-react";
import api from "@/lib/api";
import axios from "axios";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // Clear errors when switching modes
  useEffect(() => {
    setErrorMsg("");
  }, [isLogin]);

  const handleAuth = async () => {
    if (!username || !password) {
      setErrorMsg("Fill both input channels to manifest.");
      return;
    }

    setLoading(true);
    setErrorMsg("");

    try {
      if (isLogin) {
        // Construct standard URL-encoded form data as expected by FastAPI OAuth2PasswordRequestForm
        const params = new URLSearchParams();
        params.append("username", username);
        params.append("password", password);

        const response = await api.post("/auth/login", params, {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        });

        localStorage.setItem("token", response.data.access_token);
        localStorage.setItem("username", username);
        
        // Success redirect
        window.location.href = "/dashboard";
      } else {
        // Register takes raw JSON payload
        await api.post("/auth/register", { username, password });
        setIsLogin(true);
        setErrorMsg("Manifestation complete. Log in to enter the void.");
      }
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setErrorMsg(err.response.data.detail);
      } else {
        setErrorMsg("The Void rejected your credentials. Try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-void flex items-center justify-center p-6 relative overflow-hidden font-sans">
      {/* Decorative Grid Background */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f29370a_1px,transparent_1px),linear-gradient(to_bottom,#1f29370a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none" />

      {/* Cybernetic Aura Gradients */}
      <div className="absolute top-[-20%] left-[-20%] w-[60%] h-[60%] bg-ghost-cyan/15 blur-[150px] rounded-full pointer-events-none animate-pulse duration-5000" />
      <div className="absolute bottom-[-20%] right-[-20%] w-[60%] h-[60%] bg-ghost-lime/15 blur-[150px] rounded-full pointer-events-none animate-pulse duration-5000" />

      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="w-full max-w-md z-10"
      >
        <div className="glass p-8 md:p-10 rounded-[2.5rem] border border-white/5 shadow-2xl relative">
          
          {/* Subtle top border glow */}
          <div className="absolute top-0 left-1/4 right-1/4 h-[2px] bg-spectral-gradient opacity-80" />

          {/* Heading Section */}
          <div className="flex flex-col items-center mb-8">
            <motion.div 
              whileHover={{ rotate: 10, scale: 1.1 }}
              className="w-16 h-16 bg-spectral-gradient rounded-2xl flex items-center justify-center mb-4 shadow-[0_0_30px_rgba(0,255,255,0.25)] cursor-pointer"
            >
              <Ghost className="text-void w-9 h-9" />
            </motion.div>
            
            <h1 className="text-4xl font-extrabold tracking-tighter text-transparent bg-clip-text bg-spectral-gradient select-none">
              VIBEHACK
            </h1>
            <p className="text-gray-500 text-xs font-mono uppercase tracking-[0.3em] mt-2">
              {isLogin ? "Anchor Session Access" : "Create Ghost Anchor"}
            </p>
          </div>

          {/* Form Content */}
          <div className="space-y-4">
            
            {/* Error Message Box */}
            <AnimatePresence mode="wait">
              {errorMsg && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className={`p-4 rounded-2xl border text-sm font-mono flex items-start gap-3 ${
                    errorMsg.includes("complete") 
                      ? "bg-ghost-lime/10 border-ghost-lime/30 text-ghost-lime" 
                      : "bg-red-500/10 border-red-500/30 text-red-400"
                  }`}
                >
                  {errorMsg.includes("complete") ? (
                    <Sparkles className="w-5 h-5 flex-shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                  )}
                  <span>{errorMsg}</span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Username Input */}
            <div className="relative group">
              <Ghost className="absolute left-4 top-4 w-5 h-5 text-gray-500 group-focus-within:text-ghost-cyan transition-colors" />
              <input 
                type="text" 
                placeholder="Identity Username"
                value={username}
                className="w-full pl-12 pr-4 py-4 bg-black/40 border border-white/10 rounded-2xl focus:border-ghost-cyan outline-none transition-all font-mono text-sm text-ghost-white placeholder-gray-600 focus:shadow-[0_0_20px_rgba(0,255,255,0.05)]"
                onChange={(e) => setUsername(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAuth()}
              />
            </div>

            {/* Password Input (Fixed state binding!) */}
            <div className="relative group">
              <ShieldCheck className="absolute left-4 top-4 w-5 h-5 text-gray-500 group-focus-within:text-ghost-lime transition-colors" />
              <input 
                type="password" 
                placeholder="Security Key"
                value={password}
                className="w-full pl-12 pr-4 py-4 bg-black/40 border border-white/10 rounded-2xl focus:border-ghost-lime outline-none transition-all font-mono text-sm text-ghost-white placeholder-gray-600 focus:shadow-[0_0_20px_rgba(57,255,20,0.05)]"
                onChange={(e) => setPassword(e.target.value)} // Fixed from setUsername
                onKeyDown={(e) => e.key === "Enter" && handleAuth()}
              />
            </div>

            {/* Manifest Button */}
            <motion.button 
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleAuth}
              disabled={loading}
              className="w-full py-4 mt-2 bg-spectral-gradient text-void font-bold rounded-2xl flex items-center justify-center gap-2 group transition-all cursor-pointer shadow-[0_4px_20px_rgba(0,255,255,0.15)] hover:shadow-[0_4px_30px_rgba(0,255,255,0.25)] text-sm font-mono tracking-wider"
            >
              {loading ? (
                <span className="animate-pulse">RESONATING THE VOID...</span>
              ) : (
                <>
                  {isLogin ? "MANIFEST IDENTITY" : "INITIALIZE ANCHOR"}
                  <Zap className="w-4 h-4 group-hover:fill-current transition-colors" />
                </>
              )}
            </motion.button>
          </div>

          {/* Toggle Register / Login */}
          <div className="mt-8 pt-6 border-t border-white/5 text-center">
            <button 
              onClick={() => setIsLogin(!isLogin)}
              className="text-gray-500 text-sm font-mono hover:text-ghost-cyan transition-colors"
            >
              {isLogin ? "Need a permanent anchor? Initialize" : "Already registered? Manifest"}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
