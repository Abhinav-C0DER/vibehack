"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { 
  Ghost, Sparkles, LogOut, Gift, Edit3, Save, Plus, 
  Hash, Users, MessageSquare, Compass, Radio
} from "lucide-react";
import api from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [recommendedRooms, setRecommendedRooms] = useState<any[]>([]);
  const [otherRooms, setOtherRooms] = useState<any[]>([]);
  const [matchedKeywords, setMatchedKeywords] = useState<string[]>([]);
  const [newRoomName, setNewRoomName] = useState("");
  const [newRoomCategory, setNewRoomCategory] = useState("General");
  const [bio, setBio] = useState("");
  const [isEditingBio, setIsEditingBio] = useState(false);
  const [updatingBio, setUpdatingBio] = useState(false);
  const [loadingRooms, setLoadingRooms] = useState(true);

  useEffect(() => {
    // 1. Check Auth
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/");
      return;
    }

    // 2. Fetch Profile & Rooms
    fetchProfile();
    fetchRooms();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await api.get("/users/me");
      setUser(response.data);
      setBio(response.data.bio || "");
    } catch (err) {
      // Token expired or invalid
      localStorage.removeItem("token");
      localStorage.removeItem("username");
      router.push("/");
    }
  };

  const fetchRooms = async () => {
    setLoadingRooms(true);
    try {
      const response = await api.get("/rooms/recommended");
      setRecommendedRooms(response.data.recommended_rooms || []);
      setOtherRooms(response.data.other_rooms || []);
      setMatchedKeywords(response.data.matched_keywords || []);
    } catch (err) {
      console.error("Failed to load recommended rooms");
    } finally {
      setLoadingRooms(false);
    }
  };

  const handleUpdateBio = async () => {
    setUpdatingBio(true);
    try {
      const response = await api.put("/users/me", { bio });
      setUser(response.data);
      setIsEditingBio(false);
      // Refresh rooms since recommendations depend on bio!
      fetchRooms();
    } catch (err) {
      alert("Failed to update bio in the void.");
    } finally {
      setUpdatingBio(false);
    }
  };

  const handleCreateRoom = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRoomName) return;
    
    // Format room name (alphanumeric + dashes, no spaces)
    const formattedName = newRoomName
      .trim()
      .replace(/\s+/g, "-")
      .replace(/[^a-zA-Z0-9-]/g, "");

    if (!formattedName) return;

    // Save selected category to pass to room
    localStorage.setItem(`room_cat:${formattedName}`, newRoomCategory);
    router.push(`/room/${formattedName}`);
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    router.push("/");
  };

  // Safe DiceBear Avatar helper
  const getAvatarUrl = (seed: string) => {
    return `https://api.dicebear.com/7.x/identicon/svg?seed=${encodeURIComponent(seed)}`;
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-void flex items-center justify-center font-mono text-ghost-cyan text-sm">
        <div className="flex flex-col items-center gap-4">
          <Ghost className="w-12 h-12 animate-bounce" />
          <span className="animate-pulse">DECODING MANIFESTATION DATA...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-void text-ghost-white p-6 relative overflow-hidden font-sans">
      {/* Glow Effects */}
      <div className="absolute top-[-30%] left-[-10%] w-[50%] h-[50%] bg-ghost-cyan/5 blur-[150px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-30%] right-[-10%] w-[50%] h-[50%] bg-ghost-lime/5 blur-[150px] rounded-full pointer-events-none" />

      {/* Header */}
      <header className="max-w-7xl mx-auto mb-10 flex items-center justify-between z-10 relative">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-spectral-gradient rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(0,255,255,0.2)]">
            <Ghost className="text-void w-6 h-6" />
          </div>
          <span className="text-2xl font-black tracking-tighter bg-clip-text text-transparent bg-spectral-gradient">
            VIBEHACK
          </span>
        </div>
        <button 
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2 border border-white/5 hover:border-red-500/30 hover:bg-red-500/10 rounded-xl transition-all text-xs font-mono text-gray-500 hover:text-red-400 cursor-pointer"
        >
          <LogOut className="w-4 h-4" />
          FADE AWAY
        </button>
      </header>

      {/* Main Grid */}
      <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 z-10 relative">
        
        {/* LEFT COLUMN: PROFILE CARD */}
        <section className="lg:col-span-4 space-y-6">
          <div className="glass p-6 md:p-8 rounded-[2rem] border border-white/5 relative">
            <div className="absolute top-0 left-1/4 right-1/4 h-[1px] bg-spectral-gradient opacity-60" />
            
            <div className="flex flex-col items-center text-center">
              <div className="w-24 h-24 rounded-3xl border border-white/10 p-2 bg-black/40 shadow-inner mb-4 relative overflow-hidden group">
                <img 
                  src={getAvatarUrl(user.username)} 
                  alt="Avatar" 
                  className="w-full h-full object-cover rounded-2xl group-hover:scale-110 transition-transform duration-300"
                />
              </div>

              <h2 className="text-xl font-bold tracking-tight text-white mb-1 font-mono">
                {user.username}
              </h2>
              <div className="flex items-center gap-2 px-3 py-1 bg-ghost-lime/10 border border-ghost-lime/20 rounded-full text-ghost-lime text-xs font-mono mb-6">
                <Gift className="w-3.5 h-3.5" />
                <span>{user.auth_points} AP</span>
              </div>
            </div>

            {/* BIO EDITOR */}
            <div className="space-y-3 border-t border-white/5 pt-6">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-500 uppercase tracking-widest font-mono">
                  Identity Bio
                </span>
                {!isEditingBio ? (
                  <button 
                    onClick={() => setIsEditingBio(true)}
                    className="text-ghost-cyan text-xs font-mono flex items-center gap-1 hover:underline cursor-pointer"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    Modify
                  </button>
                ) : (
                  <div className="flex items-center gap-3">
                    <button 
                      onClick={handleUpdateBio}
                      disabled={updatingBio}
                      className="text-ghost-lime text-xs font-mono flex items-center gap-1 hover:underline cursor-pointer"
                    >
                      <Save className="w-3.5 h-3.5" />
                      Save
                    </button>
                    <button 
                      onClick={() => {
                        setBio(user.bio || "");
                        setIsEditingBio(false);
                      }}
                      className="text-gray-500 text-xs font-mono hover:underline cursor-pointer"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>

              {isEditingBio ? (
                <textarea 
                  value={bio}
                  rows={4}
                  className="w-full p-4 bg-black/40 border border-white/10 rounded-2xl focus:border-ghost-cyan outline-none text-sm text-ghost-white placeholder-gray-600 font-mono resize-none"
                  placeholder="Tell the void about your technical interests (e.g. coding, rust, gaming, music)..."
                  onChange={(e) => setBio(e.target.value)}
                />
              ) : (
                <p className="text-sm text-gray-400 font-mono bg-black/20 p-4 rounded-2xl border border-white/[0.02] italic whitespace-pre-wrap">
                  {user.bio || "A mysterious ghost manifested in the dark..."}
                </p>
              )}
            </div>
          </div>
        </section>

        {/* CENTER COLUMN: ACTIVE CHATROOMS */}
        <section className="lg:col-span-5 space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold tracking-tight text-white flex items-center gap-2 font-mono">
              <Compass className="w-5 h-5 text-ghost-cyan" />
              VOIDS MANIFESTED
            </h3>
            <button 
              onClick={fetchRooms}
              className="text-xs text-gray-500 font-mono hover:text-ghost-cyan transition-colors"
            >
              Sync Channels
            </button>
          </div>

          {loadingRooms ? (
            <div className="space-y-4">
              {[1, 2, 3].map((n) => (
                <div key={n} className="h-28 bg-white/5 border border-white/5 rounded-3xl animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="space-y-6">
              
              {/* RECOMMENDED CHATROOMS (AI Sparkle matching user's bio interests!) */}
              {recommendedRooms.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-xs font-mono text-ghost-cyan uppercase tracking-wider">
                    <Sparkles className="w-4 h-4 text-ghost-cyan animate-pulse" />
                    Recommended for Your Bio
                  </div>

                  <div className="space-y-3">
                    {recommendedRooms.map((room) => (
                      <motion.div 
                        whileHover={{ scale: 1.01, translateY: -2 }}
                        key={room.room_name}
                        onClick={() => router.push(`/room/${room.room_name}`)}
                        className="glass p-5 rounded-3xl border border-ghost-cyan/20 bg-ghost-cyan/[0.01] hover:bg-ghost-cyan/[0.04] cursor-pointer transition-all relative overflow-hidden group shadow-[0_0_15px_rgba(0,255,255,0.03)]"
                      >
                        <div className="absolute top-0 right-0 p-3 flex items-center gap-1.5 text-[10px] text-ghost-cyan font-mono border-l border-b border-ghost-cyan/10 bg-ghost-cyan/5 rounded-bl-2xl">
                          <Radio className="w-3.5 h-3.5 animate-pulse" />
                          <span>Technical Match</span>
                        </div>

                        <div className="flex items-center gap-3 mb-2">
                          <Hash className="w-5 h-5 text-ghost-cyan group-hover:rotate-12 transition-transform" />
                          <span className="font-mono font-bold text-white group-hover:text-ghost-cyan transition-colors">
                            {room.room_name}
                          </span>
                        </div>

                        <div className="flex items-center justify-between text-xs text-gray-500 font-mono">
                          <span className="px-2 py-0.5 border border-white/5 bg-white/5 rounded-md text-[10px] uppercase text-gray-400">
                            {room.category}
                          </span>
                          <div className="flex items-center gap-1.5 text-ghost-lime">
                            <Users className="w-3.5 h-3.5" />
                            <span>{room.user_count} manifest</span>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              )}

              {/* OTHER/GLOBAL TRENDING ROOMS */}
              <div className="space-y-3">
                {recommendedRooms.length > 0 && (
                  <div className="text-xs font-mono text-gray-500 uppercase tracking-wider">
                    Global Trending Channels
                  </div>
                )}

                {otherRooms.length > 0 ? (
                  <div className="space-y-3">
                    {otherRooms.map((room) => (
                      <motion.div 
                        whileHover={{ scale: 1.01, translateY: -2 }}
                        key={room.room_name}
                        onClick={() => router.push(`/room/${room.room_name}`)}
                        className="glass p-5 rounded-3xl border border-white/5 hover:border-white/10 hover:bg-white/[0.02] cursor-pointer transition-all relative overflow-hidden group"
                      >
                        <div className="flex items-center gap-3 mb-2">
                          <Hash className="w-5 h-5 text-gray-500 group-hover:text-ghost-lime group-hover:rotate-12 transition-transform" />
                          <span className="font-mono font-bold text-white group-hover:text-ghost-lime transition-colors">
                            {room.room_name}
                          </span>
                        </div>

                        <div className="flex items-center justify-between text-xs text-gray-500 font-mono">
                          <span className="px-2 py-0.5 border border-white/5 bg-white/5 rounded-md text-[10px] uppercase">
                            {room.category}
                          </span>
                          <div className="flex items-center gap-1.5 text-gray-400">
                            <Users className="w-3.5 h-3.5" />
                            <span>{room.user_count} active</span>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  recommendedRooms.length === 0 && (
                    <div className="glass p-8 rounded-3xl border border-white/5 text-center text-gray-500 font-mono text-sm py-12">
                      <MessageSquare className="w-10 h-10 mx-auto mb-3 opacity-35" />
                      The void is perfectly silent.
                      <span className="block text-xs text-gray-600 mt-2">
                        Create a room on the right to start whispering!
                      </span>
                    </div>
                  )
                )}
              </div>

            </div>
          )}
        </section>

        {/* RIGHT COLUMN: CREATE A ROOM */}
        <section className="lg:col-span-3 space-y-6">
          <div className="glass p-6 md:p-8 rounded-[2rem] border border-white/5 relative">
            <div className="absolute top-0 left-1/4 right-1/4 h-[1px] bg-spectral-gradient opacity-60" />
            
            <h3 className="text-lg font-bold tracking-tight text-white mb-6 flex items-center gap-2 font-mono">
              <Plus className="w-5 h-5 text-ghost-lime" />
              SPAWN VOID
            </h3>

            <form onSubmit={handleCreateRoom} className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs text-gray-500 font-mono uppercase tracking-widest block">
                  Room Name
                </label>
                <input 
                  type="text" 
                  placeholder="e.g. general-coding"
                  value={newRoomName}
                  required
                  className="w-full px-4 py-3 bg-black/40 border border-white/10 rounded-2xl focus:border-ghost-lime outline-none text-sm text-ghost-white placeholder-gray-600 font-mono"
                  onChange={(e) => setNewRoomName(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs text-gray-500 font-mono uppercase tracking-widest block">
                  Category Tag
                </label>
                <select 
                  value={newRoomCategory}
                  className="w-full px-4 py-3 bg-black/40 border border-white/10 rounded-2xl focus:border-ghost-lime outline-none text-sm text-ghost-white font-mono cursor-pointer"
                  onChange={(e) => setNewRoomCategory(e.target.value)}
                >
                  <option value="General">General Chill</option>
                  <option value="Coding">Coding / Tech</option>
                  <option value="Gaming">Gaming Arena</option>
                  <option value="Music">Music & Art</option>
                  <option value="Anime">Anime discussion</option>
                  <option value="AI">AI & Vector Spaces</option>
                </select>
              </div>

              <motion.button 
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                type="submit"
                className="w-full py-4 mt-2 bg-spectral-gradient text-void font-bold rounded-2xl flex items-center justify-center gap-2 group transition-all cursor-pointer text-sm font-mono tracking-wider shadow-[0_4px_20px_rgba(57,255,20,0.15)] hover:shadow-[0_4px_30px_rgba(57,255,20,0.25)]"
              >
                MANIFEST IN ROOM
              </motion.button>
            </form>
          </div>
        </section>

      </main>
    </div>
  );
}
