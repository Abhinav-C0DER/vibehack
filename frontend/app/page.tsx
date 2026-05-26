"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Ghost, ShieldCheck, Zap } from "lucide-react";
import api from "@/lib/api";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleAuth = async () => {
    setLoading(true);
    try {
      if (isLogin) {
        const response = await api.post("/auth/login", { username, password });
        localStorage.setItem("token", response.data.access_token);
        localStorage.setItem("username", username);
        window.location.href = "/dashboard";
      } else {
        await api.post("/auth/register", { username, password });
        setIsLogin(true);
        alert("Identity Created. Now manifest.");
      }
    } catch (err) {
      alert("The Void rejected your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-void flex items-center justify-center p-6 relative overflow-hidden">
      {/* Background Glow */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-ghost-cyan/10 blur-[120px] rounded-full" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-ghost-lime/10 blur-[120px] rounded-full" />

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md z-10"
      >
        <div className="glass p-8 rounded-[2rem] border border-white/5 shadow-2xl">
          <div className="flex flex-col items-center mb-8">
            <div className="w-16 h-16 bg-spectral-gradient rounded-2xl flex items-center justify-center mb-4 shadow-[0_0_30px_rgba(0,255,255,0.3)]">
              <Ghost className="text-void w-10 h-10" />
            </div>
            <h1 className="text-3xl font-black tracking-tighter text-glow-cyan">VIBEHACK</h1>
            <p className="text-gray-500 text-xs uppercase tracking-[0.3em] mt-2">
              {isLogin ? "Session Authentication" : "Identity Initialization"}
            </p>
          </div>

          <div className="space-y-4">
            <div className="relative group">
              <Ghost className="absolute left-4 top-4 w-5 h-5 text-gray-600 group-focus-within:text-ghost-cyan transition-colors" />
              <input 
                type="text" 
                placeholder="Ghost Username"
                className="w-full pl-12 pr-4 py-4 bg-black/40 border border-white/10 rounded-2xl focus:border-ghost-cyan outline-none transition-all font-mono text-sm"
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>

            <div className="relative group">
              <ShieldCheck className="absolute left-4 top-4 w-5 h-5 text-gray-600 group-focus-within:text-ghost-lime transition-colors" />
              <input 
                type="password" 
                placeholder="Security Key"
                className="w-full pl-12 pr-4 py-4 bg-black/40 border border-white/10 rounded-2xl focus:border-ghost-lime outline-none transition-all font-mono text-sm"
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>

            <motion.button 
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleAuth}
              disabled={loading}
              className="w-full py-4 bg-spectral-gradient text-void font-black rounded-2xl flex items-center justify-center gap-2 group transition-all"
            >
              {loading ? "PROCESSING..." : (
                <>
                  {isLogin ? "MANIFEST" : "INITIALIZE"}
                  <Zap className="w-4 h-4 group-hover:fill-current" />
                </>
              )}
            </motion.button>
          </div>

          <div className="mt-8 pt-6 border-t border-white/5 text-center">
            <button 
              onClick={() => setIsLogin(!isLogin)}
              className="text-gray-500 text-sm hover:text-ghost-cyan transition-colors"
            >
              {isLogin ? "Need a permanent anchor? Sign Up" : "Already verified? Log In"}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
