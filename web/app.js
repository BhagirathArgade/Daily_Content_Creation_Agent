/**
 * Daily Content Creation Agent - Interactive Web Dashboard & Real-Time Canvas Reel Player
 * Author: Bhagirath Argade
 * GitHub: https://github.com/BhagirathArgade/Daily_Content_Creation_Agent
 */

// Global State
const state = {
  currentSong: "Kesariya",
  currentMovie: "Brahmastra",
  currentVibe: "moody_monsoon",
  subtitleStyle: "Karaoke Highlight",
  isPlaying: false,
  currentTime: 0,
  duration: 26.0,
  animationFrameId: null,
  audioMuted: false,
  scenes: [],
  hookMetadata: {},
  cachedImages: [],
  audioCtx: null,
  synthInterval: null,
};

// Preset Knowledge Base
const CATALOG = {
  kesariya: {
    song: "Kesariya",
    movie: "Brahmastra",
    start: 54,
    end: 80,
    virality: 98,
    bpm: 118,
    energy: "High Euphoric Drop",
    vibe: "golden_hour",
    hook: "Kesariya tera ishq hai piya, rang jaaun jo main haath lagaun",
    lyrics: [
      { text: "Kesariya tera ishq hai piya", start: 0.0, end: 6.5 },
      { text: "Rang jaaun jo main haath lagaun", start: 6.5, end: 13.0 },
      { text: "Din beete saara teri fikr mein", start: 13.0, end: 19.5 },
      { text: "Rain saari teri khair manaun", start: 19.5, end: 26.0 },
    ],
  },
  "tum hi ho": {
    song: "Tum Hi Ho",
    movie: "Aashiqui 2",
    start: 62,
    end: 89,
    virality: 99,
    bpm: 88,
    energy: "Deep Emotional Climax",
    vibe: "moody_monsoon",
    hook: "Kyunki tum hi ho, ab tum hi ho, zindagi ab tum hi ho",
    lyrics: [
      { text: "Kyunki tum hi ho, ab tum hi ho", start: 0.0, end: 6.8 },
      { text: "Zindagi ab tum hi ho", start: 6.8, end: 13.5 },
      { text: "Chain bhi, mera dard bhi", start: 13.5, end: 20.0 },
      { text: "Meri aashiqui ab tum hi ho", start: 20.0, end: 27.0 },
    ],
  },
  "pehle bhi main": {
    song: "Pehle Bhi Main",
    movie: "Animal",
    start: 78,
    end: 105,
    virality: 97,
    bpm: 94,
    energy: "Hypnotic Synth Swell",
    vibe: "cyber_lofi",
    hook: "Pehle bhi main tumse mila hoon, pehli dafa hi milke laga",
    lyrics: [
      { text: "Pehle bhi main tumse mila hoon", start: 0.0, end: 6.8 },
      { text: "Pehli dafa hi milke laga", start: 6.8, end: 13.5 },
      { text: "Tune chhua zakhmon ko mere", start: 13.5, end: 20.2 },
      { text: "Marham sa kyun dil ko laga", start: 20.2, end: 27.0 },
    ],
  },
  "channa mereya": {
    song: "Channa Mereya",
    movie: "Ae Dil Hai Mushkil",
    start: 132,
    end: 159,
    virality: 98,
    bpm: 76,
    energy: "Tear-Jerking Crescendo",
    vibe: "dark_academia",
    hook: "Accha chalta hoon, duaon mein yaad rakhna",
    lyrics: [
      { text: "Accha chalta hoon, duaon mein yaad rakhna", start: 0.0, end: 6.8 },
      { text: "Mere zikr ka zubaan pe swaad rakhna", start: 6.8, end: 13.5 },
      { text: "Dil ke sandookon mein mere acche kaam rakhna", start: 13.5, end: 20.2 },
      { text: "Channa mereya mereya, channa mereya", start: 20.2, end: 27.0 },
    ],
  },
  starboy: {
    song: "Starboy",
    movie: "The Weeknd",
    start: 36,
    end: 62,
    virality: 95,
    bpm: 186,
    energy: "Driving Cyber Bassline",
    vibe: "cyber_lofi",
    hook: "Look what you've done, I'm a motherf***ing starboy",
    lyrics: [
      { text: "Every day a star is born, feel alone", start: 0.0, end: 6.5 },
      { text: "I'm in the blue Mulsanne bumping sound", start: 6.5, end: 13.0 },
      { text: "House so empty need a centerpiece", start: 13.0, end: 19.5 },
      { text: "Look what you've done, I'm a starboy", start: 19.5, end: 26.0 },
    ],
  },
  "golden hour": {
    song: "Golden Hour",
    movie: "JVKE",
    start: 52,
    end: 79,
    virality: 97,
    bpm: 94,
    energy: "Glittering Piano Surge",
    vibe: "golden_hour",
    hook: "It was just two lovers, sittin' in the car, listenin' to Blonde",
    lyrics: [
      { text: "It was just two lovers sittin' in the car", start: 0.0, end: 6.8 },
      { text: "Listenin' to Blonde, fallin' for each other", start: 6.8, end: 13.5 },
      { text: "Pink and orange skies, feelin' super fine", start: 13.5, end: 20.2 },
      { text: "Don't you waste my time, golden hour glow", start: 20.2, end: 27.0 },
    ],
  },
};

// Curated Aesthetic Imagery Matching Each Vibe
const AESTHETIC_ASSETS = {
  moody_monsoon: [
    "https://images.unsplash.com/photo-1515694346937-94d85e41e6f0?w=1080&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1509114397022-ed747cca3f65?w=1080&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1080&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1514565131-fce0801e5785?w=1080&auto=format&fit=crop&q=80"
  ],
  golden_hour: [
    "https://images.unsplash.com/photo-1495616811223-4d98c6e9c869?w=1080&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1080&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1470240731273-7821a6eeb6bd?w=1080&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1519741497674-611481863552?w=1080&auto=format&fit=crop&q=80"
  ],
  cyber_lofi: [
    "https://images.unsplash.com/photo-1508739773434-c26b3d09e071?w=1080&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1519501025264-65ba15a82390?w=1080&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=1080&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=1080&auto=format&fit=crop&q=80"
  ],
  dark_academia: [
    "https://images.unsplash.com/photo-1506880018603-83d5b814b5a6?w=1080&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1457369804613-52c61a468e7d?w=1080&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=1080&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=1080&auto=format&fit=crop&q=80"
  ],
  anime_dreamscape: [
    "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1080&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=1080&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1080&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1080&auto=format&fit=crop&q=80"
  ]
};

// DOM Elements
const canvas = document.getElementById("reelCanvas");
const ctx = canvas.getContext("2d");
const playPauseBtn = document.getElementById("playPauseBtn");
const playIcon = document.getElementById("playIcon");
const restartBtn = document.getElementById("restartBtn");
const toggleAudioBtn = document.getElementById("toggleAudioBtn");
const volumeIcon = document.getElementById("volumeIcon");
const downloadReelBtn = document.getElementById("downloadReelBtn");
const reelProgressBar = document.getElementById("reelProgressBar");
const reelCurrentTime = document.getElementById("reelCurrentTime");
const reelTotalTime = document.getElementById("reelTotalTime");
const canvasAudioTag = document.getElementById("canvasAudioTag");
const pipelineForm = document.getElementById("pipelineForm");
const generateBtn = document.getElementById("generateBtn");
const copyCaptionBtn = document.getElementById("copyCaptionBtn");
const captionContent = document.getElementById("captionContent");
const bestPostTime = document.getElementById("bestPostTime");
const storyboardScenesList = document.getElementById("storyboardScenesList");
const scenesCountBadge = document.getElementById("scenesCountBadge");
const hookTimestamp = document.getElementById("hookTimestamp");
const hookBpm = document.getElementById("hookBpm");
const hookEnergy = document.getElementById("hookEnergy");
const viralityBadge = document.getElementById("viralityBadge");
const pipelineStatusBadge = document.getElementById("pipelineStatusBadge");

// Web Audio API Synth Generator
function initAudioSynth() {
  if (!state.audioCtx) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    state.audioCtx = new AudioContext();
  }
  if (state.audioCtx.state === "suspended") {
    state.audioCtx.resume();
  }
}

function playChordBeat(bpm) {
  if (state.audioMuted || !state.audioCtx) return;

  const notes = [220, 261.63, 329.63, 392.0]; // Am7 vibe
  const osc = state.audioCtx.createOscillator();
  const gain = state.audioCtx.createGain();

  const freq = notes[Math.floor(Math.random() * notes.length)];
  osc.type = "sine";
  osc.frequency.setValueAtTime(freq, state.audioCtx.currentTime);

  gain.gain.setValueAtTime(0.08, state.audioCtx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.0001, state.audioCtx.currentTime + 0.8);

  osc.connect(gain);
  gain.connect(state.audioCtx.destination);

  osc.start();
  osc.stop(state.audioCtx.currentTime + 0.8);
}

// Preload Images
function preloadImages(imageUrls) {
  state.cachedImages = [];
  return Promise.all(
    imageUrls.map((url) => {
      return new Promise((resolve) => {
        const img = new Image();
        img.crossOrigin = "anonymous";
        img.onload = () => {
          state.cachedImages.push(img);
          resolve(img);
        };
        img.onerror = () => {
          // Fallback colored canvas if remote block
          const fallback = document.createElement("canvas");
          fallback.width = 540;
          fallback.height = 960;
          const fctx = fallback.getContext("2d");
          fctx.fillStyle = "#1e1b4b";
          fctx.fillRect(0, 0, 540, 960);
          state.cachedImages.push(fallback);
          resolve(fallback);
        };
        img.src = url;
      });
    })
  );
}

// Execute Pipeline Simulation & Render
async function runMultiAgentPipeline(song, movie, vibe, subStyle) {
  state.currentSong = song;
  state.currentMovie = movie;
  state.currentVibe = vibe;
  state.subtitleStyle = subStyle;

  // Visual status update
  pipelineStatusBadge.textContent = "Multi-Agents Working...";
  pipelineStatusBadge.className = "text-xs font-bold px-3 py-1 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30 animate-pulse";
  
  const step1 = document.getElementById("stepAgent1");
  const step2 = document.getElementById("stepAgent2");
  const step3 = document.getElementById("stepAgent3");

  step1.className = "step-indicator active";
  step2.className = "step-indicator";
  step3.className = "step-indicator";

  // Try calling backend API first if served via server.py
  let serverData = null;
  try {
    const resp = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        song_name: song,
        movie_or_artist: movie,
        vibe_theme: vibe,
        subtitle_style: subStyle,
      }),
    });
    if (resp.ok) {
      serverData = await resp.json();
    }
  } catch (err) {
    // Graceful offline / client-side standalone execution
  }

  // Step 1: Agent 1 (Viral Audio & Hook Extractor)
  await new Promise((r) => setTimeout(r, 600));
  const normKey = song.toLowerCase().trim();
  let trackInfo = serverData?.agent1_output
    ? {
        song: serverData.agent1_output.song_name,
        movie: serverData.agent1_output.movie_or_artist,
        start: serverData.agent1_output.start_sec,
        end: serverData.agent1_output.end_sec,
        virality: serverData.agent1_output.virality_score,
        bpm: serverData.agent1_output.bpm,
        energy: serverData.agent1_output.energy_level,
        vibe: vibe,
        hook: serverData.agent1_output.key_hook_line,
        lyrics: serverData.agent2_output?.scenes?.map((s) => ({
          text: s.chunk.text,
          start: s.chunk.start_time,
          end: s.chunk.end_time,
        })) || [],
      }
    : CATALOG[normKey];

  if (!trackInfo) {
    // Dynamic Fallback
    trackInfo = {
      song: song,
      movie: movie || "Cinematic Original",
      start: 48,
      end: 74,
      virality: 94,
      bpm: 104,
      energy: "Dynamic Climax Drop",
      vibe: vibe,
      hook: `Peak viral chorus of ${song}`,
      lyrics: [
        { text: `Viral hook line of ${song}`, start: 0.0, end: 6.5 },
        { text: `Heartfelt resonance from ${movie || "Original"}`, start: 6.5, end: 13.0 },
        { text: "Cinematic rhythm & aesthetic visuals", start: 13.0, end: 19.5 },
        { text: "Final drop of the viral reel", start: 19.5, end: 26.0 },
      ],
    };
  }

  state.duration = trackInfo.end - trackInfo.start;
  state.hookMetadata = trackInfo;

  hookTimestamp.textContent = `${trackInfo.start}s - ${trackInfo.end}s (${state.duration}s)`;
  hookBpm.textContent = `${trackInfo.bpm} BPM`;
  hookEnergy.textContent = trackInfo.energy;
  viralityBadge.textContent = `${trackInfo.virality}% Viral Confidence`;
  canvasAudioTag.textContent = `${trackInfo.song} • ${trackInfo.movie}`;
  reelTotalTime.textContent = `00:${Math.round(state.duration).toString().padStart(2, "0")}`;

  step1.className = "step-indicator completed";
  step2.className = "step-indicator active";

  // Step 2: Agent 2 (Lyrical Breakdown & Storyboarder)
  await new Promise((r) => setTimeout(r, 700));
  const vibeAssets = AESTHETIC_ASSETS[vibe] || AESTHETIC_ASSETS.moody_monsoon;
  
  state.scenes = trackInfo.lyrics.map((chunk, idx) => {
    return {
      id: idx + 1,
      text: chunk.text,
      start: chunk.start,
      end: chunk.end,
      imageUrl: vibeAssets[idx % vibeAssets.length],
      motion: idx % 2 === 0 ? "zoom_in" : "zoom_out",
    };
  });

  scenesCountBadge.textContent = `${state.scenes.length} Scenes Synchronized`;

  // Render Storyboard cards
  storyboardScenesList.innerHTML = "";
  state.scenes.forEach((scene) => {
    const card = document.createElement("div");
    card.className = "flex items-center space-x-3 p-2 rounded-xl bg-slate-950/80 border border-slate-800 text-xs";
    card.innerHTML = `
      <img src="${scene.imageUrl}" class="w-10 h-10 object-cover rounded-lg border border-slate-700 flex-shrink-0" alt="scene">
      <div class="flex-1 min-w-0">
        <div class="font-bold text-slate-200 truncate">"${scene.text}"</div>
        <div class="text-[10px] text-slate-400 font-mono">${scene.start}s - ${scene.end}s • ${vibe.replace('_', ' ').toUpperCase()}</div>
      </div>
      <span class="text-[10px] px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-mono">#${scene.id}</span>
    `;
    storyboardScenesList.appendChild(card);
  });

  await preloadImages(state.scenes.map((s) => s.imageUrl));

  step2.className = "step-indicator completed";
  step3.className = "step-indicator active";

  // Step 3: Agent 3 (Kinetic Video Compositor & Content Ready Engine)
  await new Promise((r) => setTimeout(r, 600));

  const captionText = 
`POV: It's 2 AM and this part of '${trackInfo.song}' hits your soul like nothing else... 🌧️🎧

🎵 Track: ${trackInfo.song}
🎬 Film / Artist: ${trackInfo.movie}
✨ Vibe: ${vibe.replace('_', ' ').toUpperCase()}
💬 Key Line: "${trackInfo.hook}"

Which song should the AI agents produce tomorrow? Drop your requests below! 👇

━━━━━━━━━━━━━━━━━━━━
🎬 Produced autonomously by Multi-Agent AI System
👑 Curated by Author: Bhagirath Argade
🔗 GitHub: https://github.com/BhagirathArgade/Daily_Content_Creation_Agent

#reelsindia #trendingreels #explorepage #viralreels #instagramreels #cinematicreels #filmgrain #moodyaesthetic #${trackInfo.song.toLowerCase().replace(/[^a-z0-9]/g, '')} #${trackInfo.movie.toLowerCase().replace(/[^a-z0-9]/g, '')} #instamusic`;

  captionContent.textContent = captionText;
  bestPostTime.textContent = "Today at 07:15 PM IST";

  step3.className = "step-indicator completed";
  pipelineStatusBadge.textContent = "Content Ready to Post!";
  pipelineStatusBadge.className = "text-xs font-bold px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";

  // Auto-play the created reel
  state.currentTime = 0;
  playReel();
}

// Canvas Drawing Engine for 9:16 Video Player
function renderCanvasFrame() {
  const width = canvas.width;
  const height = canvas.height;

  // Find active scene based on currentTime
  let activeScene = state.scenes[0];
  let sceneIndex = 0;
  for (let i = 0; i < state.scenes.length; i++) {
    if (state.currentTime >= state.scenes[i].start && state.currentTime <= state.scenes[i].end) {
      activeScene = state.scenes[i];
      sceneIndex = i;
      break;
    }
  }

  // Clear
  ctx.fillStyle = "#000000";
  ctx.fillRect(0, 0, width, height);

  // 1. Draw Background Image with Ken Burns Zoom & Subtle Pan
  const currentImg = state.cachedImages[sceneIndex] || state.cachedImages[0];
  if (currentImg) {
    const sceneDuration = activeScene.end - activeScene.start;
    const progressInScene = Math.max(0, Math.min(1, (state.currentTime - activeScene.start) / sceneDuration));

    let scale = 1.05 + progressInScene * 0.12;
    if (activeScene.motion === "zoom_out") {
      scale = 1.17 - progressInScene * 0.12;
    }

    const sw = width * scale;
    const sh = height * scale;
    const dx = (width - sw) / 2;
    const dy = (height - sh) / 2;

    ctx.save();
    ctx.drawImage(currentImg, dx, dy, sw, sh);

    // 2. Color Grading Filter & Dark Vignette
    const grad = ctx.createRadialGradient(width / 2, height / 2, width * 0.3, width / 2, height / 2, height * 0.7);
    grad.addColorStop(0, "rgba(0, 0, 0, 0.2)");
    grad.addColorStop(1, "rgba(0, 0, 0, 0.75)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);

    // 3. Film Grain Overlay Simulation
    ctx.fillStyle = "rgba(255, 255, 255, 0.03)";
    for (let i = 0; i < 400; i++) {
      const rx = Math.random() * width;
      const ry = Math.random() * height;
      ctx.fillRect(rx, ry, 1.5, 1.5);
    }
    ctx.restore();
  }

  // 4. Kinetic Subtitle Rendering Engine
  if (activeScene && activeScene.text) {
    ctx.save();
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    const textY = height * 0.65;

    if (state.subtitleStyle === "Karaoke Highlight") {
      // Word-by-word karaoke glow
      const words = activeScene.text.split(" ");
      const sceneProgress = (state.currentTime - activeScene.start) / (activeScene.end - activeScene.start);
      const activeWordIndex = Math.min(words.length - 1, Math.floor(sceneProgress * words.length));

      ctx.font = "800 36px 'Plus Jakarta Sans', sans-serif";

      // Calculate total text width to center properly
      let totalWidth = 0;
      const wordMetrics = words.map((w) => {
        const m = ctx.measureText(w + " ");
        totalWidth += m.width;
        return { word: w, width: m.width };
      });

      let startX = (width - totalWidth) / 2;

      wordMetrics.forEach((item, wIdx) => {
        if (wIdx === activeWordIndex) {
          // Highlight active word with glow
          ctx.shadowColor = "#f43f5e";
          ctx.shadowBlur = 24;
          ctx.fillStyle = "#ffffff";
          ctx.font = "900 40px 'Plus Jakarta Sans', sans-serif";
        } else if (wIdx < activeWordIndex) {
          ctx.shadowBlur = 0;
          ctx.fillStyle = "#fb7185";
          ctx.font = "800 36px 'Plus Jakarta Sans', sans-serif";
        } else {
          ctx.shadowBlur = 0;
          ctx.fillStyle = "rgba(255, 255, 255, 0.4)";
          ctx.font = "700 36px 'Plus Jakarta Sans', sans-serif";
        }

        ctx.fillText(item.word, startX + item.width / 2, textY);
        startX += item.width;
      });

    } else if (state.subtitleStyle === "Cinematic Subtitle") {
      // Centered Serif 35mm film subtitle with yellow/white hue
      ctx.font = "italic 700 32px 'Outfit', serif";
      ctx.shadowColor = "rgba(0, 0, 0, 0.9)";
      ctx.shadowBlur = 12;
      ctx.fillStyle = "#fef08a"; // Soft golden film subtitle
      ctx.fillText(activeScene.text, width / 2, textY);

    } else if (state.subtitleStyle === "Bold Pop") {
      // Punchy TikTok bold pop with stroke
      ctx.font = "900 42px 'Outfit', sans-serif";
      ctx.lineWidth = 6;
      ctx.strokeStyle = "#000000";
      ctx.strokeText(activeScene.text, width / 2, textY);

      ctx.shadowColor = "#38bdf8";
      ctx.shadowBlur = 18;
      ctx.fillStyle = "#ffffff";
      ctx.fillText(activeScene.text, width / 2, textY);

    } else {
      // Typewriter letter-by-letter
      const sceneProgress = Math.max(0, Math.min(1, (state.currentTime - activeScene.start) / (activeScene.end - activeScene.start)));
      const visibleChars = Math.floor(sceneProgress * activeScene.text.length);
      const partialText = activeScene.text.substring(0, visibleChars);

      ctx.font = "600 30px 'JetBrains Mono', monospace";
      ctx.fillStyle = "#ffffff";
      ctx.shadowColor = "rgba(0, 0, 0, 0.8)";
      ctx.shadowBlur = 8;
      ctx.fillText(partialText, width / 2, textY);
    }

    ctx.restore();
  }

  // 5. Minimalist Watermark / Creator Branding on Bottom
  ctx.save();
  ctx.textAlign = "center";
  ctx.font = "600 16px 'Plus Jakarta Sans', sans-serif";
  ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
  ctx.fillText("Curated by Bhagirath Argade", width / 2, height * 0.94);
  ctx.restore();
}

// Playback Loop
let lastTimestamp = 0;
function animatePlayback(timestamp) {
  if (!state.isPlaying) return;

  if (!lastTimestamp) lastTimestamp = timestamp;
  const delta = (timestamp - lastTimestamp) / 1000;
  lastTimestamp = timestamp;

  state.currentTime += delta;
  if (state.currentTime >= state.duration) {
    state.currentTime = 0; // Loop playback
  }

  // Update UI scrubber
  const progressPercent = (state.currentTime / state.duration) * 100;
  reelProgressBar.style.width = `${progressPercent}%`;
  reelCurrentTime.textContent = `00:${Math.floor(state.currentTime).toString().padStart(2, "0")}`;

  renderCanvasFrame();

  state.animationFrameId = requestAnimationFrame(animatePlayback);
}

function playReel() {
  initAudioSynth();
  state.isPlaying = true;
  lastTimestamp = 0;
  playIcon.className = "fa-solid fa-pause text-xs";
  
  // Start rhythmic audio pulse
  if (state.synthInterval) clearInterval(state.synthInterval);
  const bpm = state.hookMetadata.bpm || 110;
  const intervalMs = (60 / bpm) * 1000;
  state.synthInterval = setInterval(() => {
    if (state.isPlaying) playChordBeat(bpm);
  }, intervalMs);

  state.animationFrameId = requestAnimationFrame(animatePlayback);
}

function pauseReel() {
  state.isPlaying = false;
  playIcon.className = "fa-solid fa-play text-xs";
  if (state.animationFrameId) {
    cancelAnimationFrame(state.animationFrameId);
  }
  if (state.synthInterval) {
    clearInterval(state.synthInterval);
  }
}

// Event Listeners
playPauseBtn.addEventListener("click", () => {
  if (state.isPlaying) {
    pauseReel();
  } else {
    playReel();
  }
});

restartBtn.addEventListener("click", () => {
  state.currentTime = 0;
  renderCanvasFrame();
  if (!state.isPlaying) {
    playReel();
  }
});

toggleAudioBtn.addEventListener("click", () => {
  state.audioMuted = !state.audioMuted;
  volumeIcon.className = state.audioMuted ? "fa-solid fa-volume-xmark text-xs" : "fa-solid fa-volume-high text-xs";
});

// Download Reel via MediaRecorder
downloadReelBtn.addEventListener("click", () => {
  downloadReelBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i><span>Recording...</span>`;
  
  // Capture stream from canvas
  const stream = canvas.captureStream(30);
  const mediaRecorder = new MediaRecorder(stream, { mimeType: "video/webm" });
  const recordedChunks = [];

  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) recordedChunks.push(e.data);
  };

  mediaRecorder.onstop = () => {
    const blob = new Blob(recordedChunks, { type: "video/webm" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${state.currentSong.toLowerCase().replace(/\s+/g, '_')}_reel_9x16.webm`;
    a.click();
    URL.revokeObjectURL(url);
    downloadReelBtn.innerHTML = `<i class="fa-solid fa-check"></i><span>Downloaded!</span>`;
    setTimeout(() => {
      downloadReelBtn.innerHTML = `<i class="fa-solid fa-download"></i><span>Export MP4</span>`;
    }, 2000);
  };

  state.currentTime = 0;
  if (!state.isPlaying) playReel();
  mediaRecorder.start();

  // Record for 6 seconds as a sample reel or full duration
  const recordDuration = Math.min(state.duration, 8);
  setTimeout(() => {
    mediaRecorder.stop();
  }, recordDuration * 1000);
});

// Copy Caption & Hashtags
copyCaptionBtn.addEventListener("click", () => {
  navigator.clipboard.writeText(captionContent.textContent).then(() => {
    copyCaptionBtn.innerHTML = `<i class="fa-solid fa-check text-emerald-400"></i><span class="text-emerald-400">Copied!</span>`;
    setTimeout(() => {
      copyCaptionBtn.innerHTML = `<i class="fa-regular fa-copy"></i><span>Copy Caption</span>`;
    }, 2000);
  });
});

// Form Submission
pipelineForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const song = document.getElementById("songName").value.trim();
  const movie = document.getElementById("movieName").value.trim();
  const checkedVibe = document.querySelector('input[name="vibe"]:checked').value;
  const subStyle = document.getElementById("subtitleStyle").value;

  runMultiAgentPipeline(song, movie, checkedVibe, subStyle);
});

// Preset Chips
document.querySelectorAll(".preset-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".preset-chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");

    const song = chip.getAttribute("data-song");
    const movie = chip.getAttribute("data-movie");
    const vibe = chip.getAttribute("data-vibe");

    document.getElementById("songName").value = song;
    document.getElementById("movieName").value = movie;

    // Update Vibe selection
    const radio = document.querySelector(`input[name="vibe"][value="${vibe}"]`);
    if (radio) {
      radio.checked = true;
      document.querySelectorAll(".vibe-card").forEach((card) => {
        card.classList.toggle("active", card.getAttribute("data-vibe") === vibe);
      });
    }

    const subStyle = document.getElementById("subtitleStyle").value;
    runMultiAgentPipeline(song, movie, vibe, subStyle);
  });
});

// Vibe Cards Selection
document.querySelectorAll(".vibe-card").forEach((card) => {
  card.addEventListener("click", () => {
    document.querySelectorAll(".vibe-card").forEach((c) => c.classList.remove("active"));
    card.classList.add("active");
  });
});

// Initial Auto Run on Load
window.addEventListener("DOMContentLoaded", () => {
  runMultiAgentPipeline("Kesariya", "Brahmastra", "moody_monsoon", "Karaoke Highlight");
});
