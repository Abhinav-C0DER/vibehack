"use client";

import { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { io, Socket } from "socket.io-client";
import { 
  Ghost, Hash, Users, Send, ArrowLeft, ShieldAlert, Gift, 
  MessageSquareOff, MessageSquare, Sparkles, Radio, Check, X, ShieldAlert as ReportIcon
} from "lucide-react";
import api from "@/lib/api";

interface ChatMessage {
  id: string;
  sender: string;
  message: string;
  is_whisper: boolean;
  toGhostName?: string; // Optional field for local visual whispers
  is_system?: boolean;
}

export default function RoomPage() {
  const params = useParams();
  const router = useRouter();
  
  const roomName = typeof params.roomName === "string" ? params.roomName : "";
  const [roomCategory, setRoomCategory] = useState("General");
  
  const [username, setUsername] = useState("");
  const [myGhostName, setMyGhostName] = useState("");
  const [activeUsers, setActiveUsers] = useState<string[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [connected, setConnected] = useState(false);

  // Whisper details
  const [whisperTarget, setWhisperTarget] = useState<{ ghostName: string; sid: string } | null>(null);

  // Inspected ghost profile details
  const [inspectedGhost, setInspectedGhost] = useState<any | null>(null);
  const [inspectedProfile, setInspectedProfile] = useState<any | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(false);

  // Animations/Success banners
  const [successMsg, setSuccessMsg] = useState("");

  const socketRef = useRef<Socket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    // 1. Verify Authentication
    const token = localStorage.getItem("token");
    const storedUser = localStorage.getItem("username");
    if (!token || !storedUser) {
      router.push("/");
      return;
    }
    setUsername(storedUser);

    // Retrieve category from storage
    const category = localStorage.getItem(`room_cat:${roomName}`) || "General";
    setRoomCategory(category);

    // 2. Connect Sockets on http://localhost:8000
    const socket = io("http://localhost:8000");
    socketRef.current = socket;

    socket.on("connect", () => {
      setConnected(true);
      
      // Emit Join Room and handle callbacks
      socket.emit("join_room", {
        room_name: roomName,
        category: category,
        permanent_username: storedUser
      }, (response: any) => {
        if (response.status === "rejected") {
          alert(response.error || "Manifestation rejected by the void.");
          router.push("/dashboard");
        } else {
          setMyGhostName(response.username);
        }
      });
    });

    socket.on("disconnect", () => {
      setConnected(false);
      setMessages((prev) => [
        ...prev,
        {
          id: `sys-${Date.now()}`,
          sender: "System",
          message: "Disconnected from the Void's frequencies.",
          is_whisper: false,
          is_system: true
        }
      ]);
    });

    socket.on("system_message", (data: any) => {
      // If we got kicked or someone banned, check if it was us
      if (data.msg.includes("EXORCISED") && data.msg.includes(myGhostName) && myGhostName !== "") {
        alert("You have been exorcised from the void (3/3 Reports).");
        localStorage.removeItem("token");
        localStorage.removeItem("username");
        router.push("/");
        return;
      }
      setMessages((prev) => [
        ...prev,
        {
          id: `sys-${Date.now()}`,
          sender: "System",
          message: data.msg,
          is_whisper: false,
          is_system: true
        }
      ]);
    });

    socket.on("receive_message", (data: any) => {
      setMessages((prev) => [
        ...prev,
        {
          id: `msg-${Date.now()}-${Math.random()}`,
          sender: data.sender,
          message: data.message,
          is_whisper: data.is_whisper
        }
      ]);
    });

    socket.on("room_users", (data: any) => {
      setActiveUsers(data.users || []);
    });

    // 3. Heartbeat loop (every 10 seconds)
    const heartbeatInterval = setInterval(() => {
      if (socket.connected) {
        socket.emit("heartbeat");
      }
    }, 10000);

    // Clean up
    return () => {
      clearInterval(heartbeatInterval);
      if (socket) {
        socket.disconnect();
      }
    };
  }, [roomName, myGhostName]);

  // Auto-scroll chat feed
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = () => {
    const text = inputText.trim();
    if (!text || !socketRef.current) return;

    if (whisperTarget) {
      // Send private whisper
      socketRef.current.emit("whisper", {
        target_sid: whisperTarget.sid,
        message: text
      });

      // Manually append locally so the sender has visual history of their whisper!
      setMessages((prev) => [
        ...prev,
        {
          id: `whisper-local-${Date.now()}`,
          sender: myGhostName,
          message: text,
          is_whisper: true,
          toGhostName: whisperTarget.ghostName
        }
      ]);
    } else {
      // Send public room message
      socketRef.current.emit("send_message", {
        message: text
      });
    }

    setInputText("");
  };

  const handleInspectGhost = async (ghostName: string) => {
    setInspectedGhost(ghostName);
    setLoadingProfile(true);
    setInspectedProfile(null);
    try {
      const response = await api.get(`/users/ghost/${ghostName}`);
      setInspectedProfile(response.data);
    } catch (err) {
      console.error("Failed to fetch ghost profile info");
    } finally {
      setLoadingProfile(false);
    }
  };

  const handleGiftAP = async () => {
    if (!inspectedGhost) return;
    try {
      const response = await api.post(`/users/gift/${inspectedGhost}`);
      setSuccessMsg(`Successfully gifted a reputation point to ${inspectedGhost}!`);
      // Update local profile view
      if (inspectedProfile) {
        setInspectedProfile((prev: any) => ({
          ...prev,
          auth_points: (prev.auth_points || 0) + 1
        }));
      }
      setTimeout(() => setSuccessMsg(""), 3000);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Points transaction failed.");
    }
  };

  const handleReportGhost = async () => {
    if (!inspectedGhost) return;
    if (!confirm(`Are you sure you want to report ${inspectedGhost} for fake/bot activity? 3 reports will ban them permanently.`)) return;

    try {
      const response = await api.post(`/users/report/${inspectedGhost}?room_name=${roomName}`);
      setSuccessMsg(`Report registered! Status: ${response.data.reports}/3 Flags.`);
      
      // Close modal
      setInspectedGhost(null);
      setInspectedProfile(null);
      setTimeout(() => setSuccessMsg(""), 4000);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Report registration failed.");
    }
  };

  const triggerWhisper = () => {
    if (inspectedProfile && inspectedProfile.sid) {
      setWhisperTarget({
        ghostName: inspectedProfile.ghost_name,
        sid: inspectedProfile.sid
      });
      // Close profile inspector
      setInspectedGhost(null);
      setInspectedProfile(null);
    } else {
      alert("This ghost has already faded away and cannot receive whispers.");
    }
  };

  const cancelWhisper = () => {
    setWhisperTarget(null);
  };

  // Safe DiceBear Avatar helper
  const getAvatarUrl = (seed: string) => {
    return `https://api.dicebear.com/7.x/identicon/svg?seed=${encodeURIComponent(seed)}`;
  };

  return (
    <div className="min-h-screen bg-void text-ghost-white flex flex-col relative overflow-hidden font-sans">
      {/* Background Gradients */}
      <div className="absolute top-[-30%] left-[-10%] w-[50%] h-[50%] bg-ghost-cyan/5 blur-[150px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-30%] right-[-10%] w-[50%] h-[50%] bg-ghost-lime/5 blur-[150px] rounded-full pointer-events-none" />

      {/* Header */}
      <header className="px-6 py-4 border-b border-white/5 glass flex items-center justify-between z-10 relative">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => router.push("/dashboard")}
            className="p-2 border border-white/5 hover:border-white/10 hover:bg-white/5 rounded-xl transition-all cursor-pointer"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          
          <div className="flex items-center gap-2">
            <Hash className="w-6 h-6 text-ghost-cyan" />
            <span className="text-xl font-bold tracking-tight text-white font-mono">
              {roomName}
            </span>
            <span className="ml-2 px-2 py-0.5 border border-ghost-cyan/20 bg-ghost-cyan/5 text-ghost-cyan rounded-md text-[10px] font-mono uppercase">
              {roomCategory}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1 bg-black/40 border border-white/5 rounded-xl text-xs font-mono">
            <Radio className={`w-3.5 h-3.5 ${connected ? "text-ghost-lime animate-pulse" : "text-red-500"}`} />
            <span>{connected ? "Void Frequency Active" : "Searching Waves..."}</span>
          </div>

          <div className="px-3 py-1 bg-spectral-gradient text-void font-bold rounded-xl text-xs font-mono shadow-[0_0_15px_rgba(0,255,255,0.15)] select-none">
            {myGhostName || "ANONYMOUS"}
          </div>
        </div>
      </header>

      {/* SUCCESS NOTIFICATION BAR */}
      <AnimatePresence>
        {successMsg && (
          <motion.div 
            initial={{ opacity: 0, y: -50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -50 }}
            className="absolute top-20 left-1/2 -translate-x-1/2 z-50 px-6 py-3 bg-ghost-lime/10 border border-ghost-lime/30 rounded-2xl text-ghost-lime text-sm font-mono flex items-center gap-2 shadow-[0_10px_30px_rgba(57,255,20,0.1)]"
          >
            <Sparkles className="w-4 h-4 animate-bounce" />
            {successMsg}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Workspace */}
      <div className="flex-1 max-w-7xl w-full mx-auto grid grid-cols-12 overflow-hidden relative z-10 p-6 gap-6 h-[calc(100vh-80px)]">
        
        {/* CHAT AREA (Grid Col 9) */}
        <div className="col-span-12 lg:col-span-9 flex flex-col h-full bg-black/20 border border-white/5 rounded-[2rem] p-6 relative overflow-hidden">
          
          {/* Scrollable Message Box */}
          <div className="flex-1 overflow-y-auto space-y-4 pr-2 select-text">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center font-mono text-gray-500 text-sm text-center">
                <MessageSquare className="w-12 h-12 text-gray-700 mb-3 animate-pulse" />
                <span>The frequencies are perfectly silent.</span>
                <span className="text-[10px] text-gray-600 mt-2 block">
                  Broadcast your voice first to manifest a whisper.
                </span>
              </div>
            ) : (
              messages.map((msg) => {
                if (msg.is_system) {
                  return (
                    <div key={msg.id} className="w-full text-center py-1">
                      <span className="px-3 py-1 bg-black/40 border border-white/5 rounded-full text-[10px] font-mono text-ghost-lime/70 italic inline-block">
                        {msg.message}
                      </span>
                    </div>
                  );
                }

                const isMe = msg.sender === myGhostName;

                return (
                  <div 
                    key={msg.id} 
                    className={`flex items-start gap-3 max-w-[80%] ${isMe ? "ml-auto flex-row-reverse" : "mr-auto"}`}
                  >
                    {/* Ghost Avatar */}
                    <div 
                      onClick={() => !isMe && handleInspectGhost(msg.sender)}
                      className={`w-9 h-9 rounded-xl border p-1 bg-black/40 flex-shrink-0 cursor-pointer overflow-hidden ${
                        msg.is_whisper 
                          ? "border-purple-500/30 hover:border-purple-400" 
                          : isMe 
                            ? "border-ghost-lime/30" 
                            : "border-ghost-cyan/30 hover:border-ghost-cyan"
                      }`}
                    >
                      <img 
                        src={getAvatarUrl(msg.sender)} 
                        alt="Ghost Avatar" 
                        className="w-full h-full object-cover rounded-lg"
                      />
                    </div>

                    {/* Message Bubble Container */}
                    <div className="flex flex-col">
                      <span 
                        onClick={() => !isMe && handleInspectGhost(msg.sender)}
                        className={`text-[10px] font-mono mb-1 cursor-pointer hover:underline ${
                          msg.is_whisper 
                            ? "text-purple-400 font-bold" 
                            : isMe 
                              ? "text-ghost-lime" 
                              : "text-ghost-cyan"
                        }`}
                      >
                        {msg.is_whisper 
                          ? isMe 
                            ? `🤫 You whispered to ${msg.toGhostName}` 
                            : `🤫 Private whisper`
                          : msg.sender}
                      </span>

                      <div className={`p-4 rounded-3xl text-sm leading-relaxed ${
                        msg.is_whisper 
                          ? "bg-purple-500/10 border border-purple-500/30 text-purple-200 rounded-tr-none" 
                          : isMe 
                            ? "bg-ghost-lime/10 border border-ghost-lime/20 text-ghost-white rounded-tr-none" 
                            : "bg-white/5 border border-white/5 text-ghost-white rounded-tl-none"
                      }`}>
                        {msg.message}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* WHISPER ALERT HEADER */}
          {whisperTarget && (
            <div className="mt-4 px-4 py-2 bg-purple-500/10 border border-purple-500/20 rounded-2xl text-xs font-mono text-purple-400 flex items-center justify-between animate-pulse">
              <span className="flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 animate-spin duration-3000" />
                Whispering to {whisperTarget.ghostName}
              </span>
              <button 
                onClick={cancelWhisper}
                className="p-1 hover:bg-purple-500/20 rounded-md transition-colors cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Message Input Box */}
          <div className="mt-4 flex gap-3">
            <input 
              type="text" 
              placeholder={
                whisperTarget 
                  ? `Send private whisper to ${whisperTarget.ghostName}...` 
                  : "Send message to room..."
              }
              value={inputText}
              className={`flex-1 px-5 py-4 bg-black/40 border rounded-2xl outline-none text-sm text-ghost-white font-mono transition-all placeholder-gray-600 ${
                whisperTarget 
                  ? "border-purple-500/30 focus:border-purple-400 focus:shadow-[0_0_20px_rgba(168,85,247,0.05)]" 
                  : "border-white/10 focus:border-ghost-cyan focus:shadow-[0_0_20px_rgba(0,255,255,0.05)]"
              }`}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSendMessage();
                if (e.key === "Escape" && whisperTarget) cancelWhisper();
              }}
            />
            <motion.button 
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleSendMessage}
              className={`px-5 py-4 font-mono font-bold rounded-2xl flex items-center justify-center gap-2 cursor-pointer shadow-lg transition-all ${
                whisperTarget 
                  ? "bg-purple-500 hover:bg-purple-600 text-white shadow-purple-500/10" 
                  : "bg-spectral-gradient text-void shadow-ghost-cyan/10"
              }`}
            >
              <Send className="w-4 h-4" />
            </motion.button>
          </div>

        </div>

        {/* SIDEBAR: ACTIVE PARTICIPANTS (Grid Col 3) */}
        <div className="col-span-12 lg:col-span-3 flex flex-col h-full bg-black/20 border border-white/5 rounded-[2rem] p-6 relative overflow-hidden">
          
          <div className="flex items-center gap-2 mb-6 text-sm font-mono text-ghost-cyan uppercase tracking-wider">
            <Users className="w-4 h-4" />
            <span>MANIFESTED ({activeUsers.length})</span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-3 pr-1">
            {activeUsers.map((user) => {
              const isMe = user === myGhostName;
              return (
                <div 
                  onClick={() => !isMe && handleInspectGhost(user)}
                  key={user}
                  className={`flex items-center justify-between p-3 rounded-2xl border transition-all cursor-pointer ${
                    isMe 
                      ? "border-ghost-lime/20 bg-ghost-lime/[0.02]" 
                      : "border-white/5 hover:border-ghost-cyan/20 hover:bg-ghost-cyan/[0.02] group"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg border border-white/10 p-0.5 bg-black/40 overflow-hidden flex-shrink-0">
                      <img 
                        src={getAvatarUrl(user)} 
                        alt="Ghost Avatar" 
                        className="w-full h-full object-cover rounded-md"
                      />
                    </div>
                    
                    <span className={`text-xs font-mono font-bold tracking-tight ${
                      isMe 
                        ? "text-ghost-lime" 
                        : "text-gray-300 group-hover:text-ghost-cyan transition-colors"
                    }`}>
                      {user}
                    </span>
                  </div>

                  {isMe && (
                    <span className="text-[9px] font-mono px-2 py-0.5 bg-ghost-lime/10 border border-ghost-lime/20 rounded-md text-ghost-lime">
                      YOU
                    </span>
                  )}
                </div>
              );
            })}
          </div>

        </div>

      </div>

      {/* GLASSMORPHIC GHOST INSPECTOR PROFILE MODAL */}
      <AnimatePresence>
        {inspectedGhost && (
          <div className="absolute inset-0 z-40 bg-black/60 backdrop-blur-md flex items-center justify-center p-6">
            
            {/* Modal Body */}
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="glass p-8 rounded-[2.5rem] border border-white/10 shadow-2xl relative w-full max-w-sm overflow-hidden"
            >
              {/* Dynamic decorative colors inside the card */}
              <div className="absolute -top-10 -right-10 w-24 h-24 bg-ghost-cyan/10 blur-xl rounded-full" />
              <div className="absolute -bottom-10 -left-10 w-24 h-24 bg-ghost-lime/10 blur-xl rounded-full" />

              {/* Top border spectral line */}
              <div className="absolute top-0 left-0 right-0 h-[2px] bg-spectral-gradient" />

              {/* Close Button */}
              <button 
                onClick={() => {
                  setInspectedGhost(null);
                  setInspectedProfile(null);
                }}
                className="absolute top-4 right-4 p-2 border border-white/5 hover:border-white/10 hover:bg-white/5 rounded-xl transition-all cursor-pointer text-gray-500 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>

              {loadingProfile ? (
                <div className="flex flex-col items-center justify-center font-mono py-12 text-sm text-ghost-cyan">
                  <Ghost className="w-8 h-8 animate-bounce mb-3" />
                  <span className="animate-pulse">DECODING GHOST SIGNATURE...</span>
                </div>
              ) : inspectedProfile ? (
                <div className="flex flex-col items-center text-center">
                  
                  {/* Large DiceBear Avatar */}
                  <div className="w-20 h-20 rounded-2xl border border-white/10 p-1.5 bg-black/40 mb-4 overflow-hidden shadow-inner">
                    <img 
                      src={getAvatarUrl(inspectedProfile.ghost_name)} 
                      alt="Large Ghost Avatar" 
                      className="w-full h-full object-cover rounded-xl"
                    />
                  </div>

                  {/* Name & Reputation AP */}
                  <h4 className="text-lg font-bold font-mono text-white tracking-tight mb-1 select-all">
                    {inspectedProfile.ghost_name}
                  </h4>
                  <div className="flex items-center gap-1.5 px-3 py-1 bg-ghost-lime/10 border border-ghost-lime/20 rounded-full text-ghost-lime text-xs font-mono mb-6">
                    <Gift className="w-3.5 h-3.5" />
                    <span>{inspectedProfile.auth_points || 0} Authenticity Points</span>
                  </div>

                  {/* BIO */}
                  <div className="w-full text-left bg-black/30 border border-white/5 p-4 rounded-2xl font-mono text-xs text-gray-400 leading-relaxed mb-6 whitespace-pre-wrap max-h-32 overflow-y-auto">
                    {inspectedProfile.bio || "This ghost remains silent, leaving no interest signature..."}
                  </div>

                  {/* ACTIONS BOX */}
                  <div className="grid grid-cols-2 gap-3 w-full border-t border-white/5 pt-6">
                    
                    {/* WHISPER ACTION */}
                    <button 
                      onClick={triggerWhisper}
                      disabled={!inspectedProfile.sid}
                      className="flex items-center justify-center gap-2 p-3 bg-purple-500 hover:bg-purple-600 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold font-mono rounded-xl transition-all cursor-pointer text-xs"
                    >
                      <MessageSquare className="w-4 h-4" />
                      WHISPER
                    </button>

                    {/* GIFT POINTS ACTION */}
                    <button 
                      onClick={handleGiftAP}
                      className="flex items-center justify-center gap-2 p-3 bg-ghost-lime hover:bg-ghost-lime/80 text-void font-bold font-mono rounded-xl transition-all cursor-pointer text-xs shadow-md shadow-ghost-lime/10"
                    >
                      <Gift className="w-4 h-4" />
                      GIFT AP
                    </button>

                  </div>

                  {/* REPORT ACTION (Moderation penality) */}
                  <button 
                    onClick={handleReportGhost}
                    className="w-full flex items-center justify-center gap-2 p-3 mt-3 border border-white/5 hover:border-red-500/20 hover:bg-red-500/10 text-gray-500 hover:text-red-400 transition-all font-mono rounded-xl cursor-pointer text-xs uppercase"
                  >
                    <ReportIcon className="w-4 h-4" />
                    Report Identity (Moderation)
                  </button>

                </div>
              ) : (
                <div className="flex flex-col items-center text-center font-mono py-8 text-sm text-red-400">
                  <MessageSquareOff className="w-8 h-8 mb-2 opacity-50" />
                  <span>Ghost has faded from the session pointer.</span>
                </div>
              )}

            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
}
