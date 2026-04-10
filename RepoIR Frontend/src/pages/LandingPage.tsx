import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  HiOutlineDocument,
  HiOutlineCloudUpload,
  HiOutlineDatabase,
  HiOutlineShare,
  HiOutlineLightningBolt,
  HiOutlineRefresh,
  HiOutlineShieldCheck,
  HiOutlineChatAlt2,
  HiOutlineSearch,
  HiOutlineLockClosed,
  HiOutlineCheckCircle,
  HiOutlineDocumentText,
  HiOutlinePhotograph,
  HiOutlineTable
} from 'react-icons/hi';

export default function LandingPage() {
  const [scrollY, setScrollY] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans overflow-x-hidden selection:bg-cyan-500/20 selection:text-cyan-900">
      
      {/* 1. Header (Transparent styling) */}
      <header className={`fixed top-0 left-0 w-full z-50 transition-all duration-500 h-24 ${scrollY > 50 ? 'bg-white/80 backdrop-blur-lg shadow-sm border-b border-slate-100' : 'bg-transparent border-transparent'}`}>
        <nav className="flex justify-between items-center max-w-7xl mx-auto px-6 h-full">
          <div className="flex items-center gap-3 scale-90 hover:scale-100 transition-transform cursor-pointer" onClick={() => navigate('/')}>
            <img src="/logo-title.png" alt="RepoIR" className="h-[144px] w-auto drop-shadow-2xl" />
          </div>
          <button onClick={() => navigate('/login')} className="bg-gradient-to-r from-cyan-400 to-blue-500 px-6 py-2.5 rounded-full text-white font-bold tracking-wide text-sm transition-all hover:scale-105 hover:shadow-[0_0_20px_rgba(83,226,247,0.4)] active:scale-95">
            Get Started
          </button>
        </nav>
      </header>

      <main className="pt-20">
        {/* 2. Hero Section (Light Mode styling with custom animations) */}
        <section className="relative min-h-[85vh] flex flex-col items-center justify-center px-6 overflow-hidden bg-[radial-gradient(circle_at_50%_50%,rgba(0,91,191,0.03)_0%,rgba(248,249,250,0)_70%)] pb-32">
          <div className="max-w-7xl mx-auto flex flex-col items-center text-center mt-20">
            <motion.h1 
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="text-6xl md:text-8xl font-black tracking-tighter text-slate-900 mb-6 max-w-5xl leading-tight"
            >
              The ultimate AI brain <br/>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-500 italic">for your files.</span>
            </motion.h1>

            <motion.p 
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="text-lg md:text-xl text-slate-600 max-w-2xl mb-24 font-medium leading-relaxed"
            >
              Break the physical limits of information. RepoIR organizes, connects, and semantically understands your data directly from Google Drive and local uploads, instantly.
            </motion.p>



            {/* Anti-Gravity Visual */}
            <motion.div 
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.5, duration: 1 }}
              className="relative w-full max-w-4xl h-[350px] flex items-center justify-center pointer-events-none"
            >
              {/* Central AI Core */}
              <div className="absolute w-40 h-40 bg-blue-500/20 rounded-full flex items-center justify-center blur-2xl animate-pulse"></div>
              <div className="absolute w-[216px] h-[216px] bg-white/10 backdrop-blur-xl border border-white/20 rounded-[3rem] flex items-center justify-center shadow-2xl z-20 overflow-hidden">
                <img src="/logo-no-title.png" alt="AI Core" className="w-48 h-48 object-contain translate-y-2" />
              </div>

              {/* Orbiting Cards */}
              <motion.div 
                animate={{ y: [0, -20, 0] }}
                transition={{ repeat: Infinity, duration: 6, ease: "easeInOut" }}
                className="absolute top-10 left-[15%]"
              >
                <div className="bg-white/90 backdrop-blur-md p-3 rounded-2xl shadow-xl border border-slate-100 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-red-50 text-red-500 flex items-center justify-center flex-shrink-0">
                    <HiOutlineDocument className="w-6 h-6" />
                  </div>
                  <div className="text-sm font-bold text-slate-800 pr-2">Q3_Financials.pdf</div>
                </div>
              </motion.div>

              <motion.div 
                animate={{ y: [0, 20, 0] }}
                transition={{ repeat: Infinity, duration: 7, ease: "easeInOut", delay: 1 }}
                className="absolute bottom-4 right-[15%]"
              >
                <div className="bg-white/90 backdrop-blur-md p-3 rounded-2xl shadow-xl border border-slate-100 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-500 flex items-center justify-center flex-shrink-0">
                    <HiOutlineDocumentText className="w-6 h-6" />
                  </div>
                  <div className="text-sm font-bold text-slate-800 pr-2">System_Architecture.docx</div>
                </div>
              </motion.div>

              <motion.div 
                animate={{ y: [0, -15, 0] }}
                transition={{ repeat: Infinity, duration: 5, ease: "easeInOut", delay: 2 }}
                className="absolute top-[45%] left-[5%]"
              >
                <div className="bg-white/90 backdrop-blur-md p-3 rounded-2xl shadow-xl border border-slate-100 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-500 flex items-center justify-center flex-shrink-0">
                    <HiOutlineTable className="w-6 h-6" />
                  </div>
                  <div className="text-sm font-bold text-slate-800 pr-2">Marketing_Assets.csv</div>
                </div>
              </motion.div>

              <motion.div 
                animate={{ y: [0, 25, 0] }}
                transition={{ repeat: Infinity, duration: 8, ease: "easeInOut", delay: 1.5 }}
                className="absolute top-5 right-[10%]"
              >
                <div className="bg-white/90 backdrop-blur-md p-3 rounded-2xl shadow-xl border border-slate-100 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-purple-50 text-purple-500 flex items-center justify-center flex-shrink-0">
                    <HiOutlinePhotograph className="w-6 h-6" />
                  </div>
                  <div className="text-sm font-bold text-slate-800 pr-2">Design_Mockup.png</div>
                </div>
              </motion.div>

            </motion.div>
          </div>
        </section>

        {/* 3. Bento Grid Features */}
        <section className="py-32 px-6 bg-slate-100/50">
          <div className="max-w-7xl mx-auto">
            <motion.div 
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="mb-16 text-center md:text-left"
            >
              <h2 className="text-4xl md:text-5xl font-black mb-4 tracking-tight text-slate-900">Your universe, organized.</h2>
              <p className="text-slate-600 max-w-2xl text-lg font-medium">Every backend feature is strictly designed to reduce structural friction and elevate your cognitive workflow via FastAPI & HuggingFace.</p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-12 gap-6 auto-rows-[300px]">
              
              {/* Semantic Search */}
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                className="md:col-span-8 bg-white rounded-3xl p-10 flex flex-col justify-between overflow-hidden relative group shadow-sm border border-slate-200/60"
              >
                <div className="relative z-10">
                  <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center mb-6">
                    <HiOutlineSearch className="w-6 h-6" />
                  </div>
                  <h3 className="text-3xl font-bold mb-4 text-slate-900">Semantic Discovery</h3>
                  <p className="text-slate-600 max-w-md text-lg leading-relaxed">Stop manually searching for exact filenames. Search natively for ideas, concepts, and relationships directly within your files.</p>
                </div>
                <div className="absolute right-[-10%] bottom-[-20%] w-[60%] h-[120%] bg-gradient-to-tl from-slate-100 to-transparent rounded-full rotate-12 pointer-events-none transition-transform duration-700 group-hover:scale-110"></div>
              </motion.div>

              {/* Instant Sync */}
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.1 }}
                className="md:col-span-4 bg-blue-600 text-white rounded-3xl p-10 flex flex-col justify-end relative overflow-hidden shadow-lg shadow-blue-600/20 group"
              >
                <div className="absolute top-8 right-8 transition-transform duration-500 group-hover:rotate-12 group-hover:scale-110">
                  <HiOutlineRefresh className="w-12 h-12 opacity-80" />
                </div>
                <h3 className="text-2xl font-bold mb-3 z-10">Instant Sync</h3>
                <p className="text-blue-100 text-sm font-medium z-10 leading-relaxed">Sync Google Drive or directly upload documents, PDFs, Images, and Web URLs—all mapped in one central vault.</p>
              </motion.div>

              {/* Natural Language Search */}
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                className="md:col-span-4 bg-white rounded-3xl p-8 flex flex-col gap-6 shadow-sm border border-slate-200/60"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <HiOutlineSearch className="text-blue-600 w-5 h-5" />
                  </div>
                  <span className="font-bold text-slate-900 text-lg">Natural Language Search</span>
                </div>
                <div className="space-y-4 flex-1 flex flex-col justify-center font-medium">
                  <div className="bg-slate-50 p-4 rounded-full text-sm w-[90%] shadow-sm text-slate-700 border border-slate-200 flex items-center gap-2">
                    <HiOutlineSearch className="w-4 h-4 text-slate-400" />
                    {"board meeting budget changes"}
                  </div>
                  <div className="bg-blue-50/50 p-4 rounded-xl text-sm w-full text-blue-700 border border-blue-100/50 flex flex-col gap-1">
                    <span className="font-bold text-xs opacity-70">Result • Board_Minutes.pdf</span>
                    <span>"...resulted in a 20% budget reallocation to AI research."</span>
                  </div>
                </div>
              </motion.div>

              {/* Security */}
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.1 }}
                className="md:col-span-8 bg-white rounded-3xl p-10 flex flex-col md:flex-row items-center gap-10 shadow-sm border border-slate-200/60 overflow-hidden"
              >
                <div className="flex-1">
                  <div className="w-12 h-12 bg-red-50 text-red-500 rounded-xl flex items-center justify-center mb-6">
                    <HiOutlineShieldCheck className="w-6 h-6" />
                  </div>
                  <h3 className="text-2xl font-bold mb-4 text-slate-900">Weightless Security</h3>
                  <p className="text-slate-600 text-lg leading-relaxed">Every document chunk is hashed and securely processed. RepoIR employs highly encrypted vault layers that never slow you down.</p>
                </div>
                <div className="flex-[0.8] bg-slate-50 h-full w-full rounded-2xl p-8 flex flex-col justify-center border border-slate-100 shadow-inner">
                  <div className="space-y-5">
                    <div className="flex items-center gap-3">
                      <HiOutlineLockClosed className="w-5 h-5 text-slate-400" />
                      <div className="h-2 w-full bg-slate-200 rounded-full overflow-hidden">
                        <motion.div animate={{ width: "100%" }} transition={{ duration: 1.5, repeat: Infinity, repeatType: 'reverse' }} className="h-full bg-blue-500 rounded-full"></motion.div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <HiOutlineLockClosed className="w-5 h-5 text-slate-400" />
                      <div className="h-2 w-full bg-slate-200 rounded-full overflow-hidden">
                        <motion.div animate={{ width: "80%" }} transition={{ duration: 2, repeat: Infinity, repeatType: 'reverse' }} className="h-full bg-emerald-500 rounded-full"></motion.div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <HiOutlineLockClosed className="w-5 h-5 text-slate-400" />
                      <div className="h-2 w-full bg-slate-200 rounded-full overflow-hidden">
                        <motion.div animate={{ width: "95%" }} transition={{ duration: 1.8, repeat: Infinity, repeatType: 'reverse' }} className="h-full bg-purple-500 rounded-full"></motion.div>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>

            </div>
          </div>
        </section>

        {/* 4. Interactive Pill Section */}
        <section className="py-32 px-6">
          <div className="max-w-4xl mx-auto text-center">
            <motion.h2 
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="text-3xl font-bold mb-10 text-slate-900"
            >
              How did you hear about us?
            </motion.h2>
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
              className="flex flex-wrap justify-center gap-4"
            >
              {['Product Hunt', 'X / Twitter', 'LinkedIn', 'Friend or Colleague', 'Tech Blog', 'HuggingFace', 'Other'].map((source) => (
                <button key={source} className="px-8 py-3.5 rounded-full bg-white border border-slate-200 text-slate-600 font-medium hover:bg-blue-600 hover:text-white hover:border-blue-600 hover:shadow-lg hover:-translate-y-1 transition-all duration-300">
                  {source}
                </button>
              ))}
            </motion.div>
          </div>
        </section>

        {/* 5. Final CTA Section */}
        <section className="py-20 px-6 mb-24">
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="max-w-5xl mx-auto rounded-[3rem] bg-gradient-to-br from-blue-600 to-cyan-500 p-16 md:p-24 text-center text-white shadow-2xl relative overflow-hidden"
          >
            {/* Animated background elements */}
            <div className="absolute top-0 right-0 w-96 h-96 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3"></div>
            <div className="absolute bottom-0 left-0 w-96 h-96 bg-cyan-300/20 rounded-full blur-3xl translate-y-1/3 -translate-x-1/3"></div>
            
            <div className="relative z-10 flex flex-col items-center">
              <h2 className="text-4xl md:text-6xl font-black mb-6 tracking-tight">Ready to curate your universe?</h2>
              <p className="text-xl md:text-2xl mb-12 text-blue-50 max-w-2xl mx-auto font-medium">Experience true information weightlessness today. Your digital brain is waiting.</p>
              <div className="flex justify-center w-full sm:w-auto">
                <button onClick={() => navigate('/login')} className="bg-white text-blue-600 px-12 py-5 rounded-2xl font-bold text-lg hover:shadow-xl hover:scale-105 transition-all duration-300 w-full sm:w-auto">
                  Get Started
                </button>
              </div>
            </div>
          </motion.div>
        </section>
      </main>

      {/* 6. Footer (Dark Mode) */}
      <footer className="w-full py-16 px-8 bg-zinc-950 font-sans border-t border-zinc-900">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center max-w-7xl mx-auto">
          
          <div className="flex flex-col gap-4 mb-10 md:mb-0">
            <div className="flex items-center gap-2 cursor-pointer transition-transform hover:scale-105">
              <div className="w-10 h-10 flex items-center justify-center overflow-hidden">
                <img src="/logo-no-title.png" alt="RepoIR" className="w-8 h-8 object-contain translate-y-1" />
              </div>
              <span className="font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500 text-2xl tracking-tight">RepoIR</span>
            </div>
            <p className="text-sm text-zinc-500 font-medium">© {new Date().getFullYear()} RepoIR. The AI Powered Archive</p>
          </div>

          <div className="flex flex-wrap gap-12 md:gap-24">
            <div className="flex flex-col gap-4">
              <span className="text-xs font-bold uppercase tracking-widest text-zinc-400">Product</span>
              <button onClick={() => window.open('https://github.com/AdityaSohner/RepoIR', '_blank')} className="text-zinc-500 hover:text-cyan-400 transition-colors text-sm font-medium text-left">Github Repo</button>
              <button className="text-zinc-500 hover:text-cyan-400 transition-colors text-sm font-medium text-left">Changelog</button>
              <button className="text-zinc-500 hover:text-cyan-400 transition-colors text-sm font-medium text-left">Security</button>
            </div>
            
            <div className="flex flex-col gap-4">
              <span className="text-xs font-bold uppercase tracking-widest text-zinc-400">Legal</span>
              <button onClick={() => alert('RepoIR maintains a strict zero-log encryption policy. All telemetry is anonymized.')} className="text-zinc-500 hover:text-cyan-400 transition-colors text-sm font-medium text-left">Privacy Policy</button>
              <button onClick={() => alert('Standard Apache 2.0 / Open Source usage terms apply.')} className="text-zinc-500 hover:text-cyan-400 transition-colors text-sm font-medium text-left">Terms of Service</button>
              <button onClick={() => alert('We do not use tracking cookies. Session cookies are strictly for JWT authentication.')} className="text-zinc-500 hover:text-cyan-400 transition-colors text-sm font-medium text-left">Cookies</button>
            </div>
          </div>

        </div>
      </footer>
    </div>
  );
}
