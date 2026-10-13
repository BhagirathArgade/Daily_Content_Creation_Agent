/**
 * Daily Content Creation Agent v2 — Interactive Web App
 * Author: Bhagirath Argade
 * GitHub: https://github.com/BhagirathArgade/Daily_Content_Creation_Agent
 *
 * Features:
 * - Real-time YouTube search suggestions as you type
 * - SSE streaming progress from backend pipeline
 * - Real video playback + image scene gallery
 * - Regenerate button for new AI visuals on same lyrics
 */

// ─── App State ───────────────────────────────────────────────────────────────
const state = {
  selectedSong: null,     // { title, channel, url, video_id, thumbnail, duration }
  selectedVibe: "bollywood_drama",
  currentScenes: [],      // scenes from last run
  currentRegenSeed: 1,
  currentAudioClip: "",  // hook clip URL from the last run
  currentVideoUrl: "",
  isProcessing: false,
  searchTimeout: null,
};

// ─── DOM Elements ─────────────────────────────────────────────────────────────
const songInput      = document.getElementById("songSearchInput");
const searchSpinner  = document.getElementById("searchSpinner");
const suggestionsDrop = document.getElementById("suggestionsDrop");
const selectedCard   = document.getElementById("selectedSongCard");
const selectedThumb  = document.getElementById("selectedThumb");
const selectedTitle  = document.getElementById("selectedTitle");
const selectedChannel= document.getElementById("selectedChannel");
const selectedDuration= document.getElementById("selectedDuration");
const clearBtn       = document.getElementById("clearSelectionBtn");
const generateBtn    = document.getElementById("generateBtn");
const generateBtnText= document.getElementById("generateBtnText");
const consoleLog     = document.getElementById("consoleLog");
const pipelineBadge  = document.getElementById("pipelineBadge");
const resultSection  = document.getElementById("resultSection");
const reelVideo      = document.getElementById("reelVideo");
const hookAudio      = document.getElementById("hookAudio");
const hookMeta       = document.getElementById("hookMeta");
const scenesGrid     = document.getElementById("scenesGrid");
const scenesCount    = document.getElementById("scenesCount");
const captionText    = document.getElementById("captionText");
const postTime       = document.getElementById("postTime");
const copyCaptionBtn = document.getElementById("copyCaptionBtn");
const downloadVideoBtn= document.getElementById("downloadVideoBtn");
const regenerateBtn  = document.getElementById("regenerateBtn");
const step1          = document.getElementById("step1");
const step2          = document.getElementById("step2");
const step3          = document.getElementById("step3");

// ─── Utility ──────────────────────────────────────────────────────────────────
function formatDuration(secs) {
  if (!secs) return "";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function logLine(msg, type = "") {
  const div = document.createElement("div");
  div.className = `log-line ${type}`;
  const now = new Date().toLocaleTimeString("en-IN", { hour12: false });
  div.textContent = `[${now}] ${msg}`;
  consoleLog.appendChild(div);
  consoleLog.scrollTop = consoleLog.scrollHeight;
}

function setStepState(step, s) {
  step.className = `step-box ${s}`;
  if (s === "done") {
    step.querySelector(".step-dot").innerHTML = '<i class="fa-solid fa-check text-[10px]"></i>';
  }
}

function resetSteps() {
  [step1, step2, step3].forEach(s => {
    s.className = "step-box";
    const dot = s.querySelector(".step-dot");
    dot.innerHTML = dot.dataset.num || dot.textContent;
  });
  step1.querySelector(".step-dot").dataset.num = "1";
  step2.querySelector(".step-dot").dataset.num = "2";
  step3.querySelector(".step-dot").dataset.num = "3";
}

// ─── SEARCH SUGGESTIONS ──────────────────────────────────────────────────────
songInput.addEventListener("input", () => {
  const q = songInput.value.trim();
  if (state.searchTimeout) clearTimeout(state.searchTimeout);

  if (q.length < 2) {
    suggestionsDrop.classList.add("hidden");
    return;
  }
  state.searchTimeout = setTimeout(() => fetchSuggestions(q), 400);
});

songInput.addEventListener("keydown", e => {
  if (e.key === "Escape") suggestionsDrop.classList.add("hidden");
});

document.addEventListener("click", e => {
  if (!e.target.closest("#searchWrapper")) {
    suggestionsDrop.classList.add("hidden");
  }
});

async function fetchSuggestions(q) {
  searchSpinner.classList.remove("hidden");
  try {
    const resp = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
    if (!resp.ok) throw new Error("Search failed");
    const data = await resp.json();
    renderSuggestions(data.results || []);
  } catch (err) {
    suggestionsDrop.classList.add("hidden");
  } finally {
    searchSpinner.classList.add("hidden");
  }
}

function renderSuggestions(results) {
  suggestionsDrop.innerHTML = "";
  if (!results.length) {
    suggestionsDrop.classList.add("hidden");
    return;
  }
  results.forEach(item => {
    if (item.error || !item.video_id) return;
    const div = document.createElement("div");
    div.className = "suggestion-item";
    const thumb = item.thumbnail || `https://img.youtube.com/vi/${item.video_id}/mqdefault.jpg`;
    const dur = formatDuration(item.duration);
    div.innerHTML = `
      <img src="${thumb}" alt="" class="w-12 h-9 rounded-lg object-cover flex-shrink-0 border border-slate-700"
           onerror="this.src='https://img.youtube.com/vi/${item.video_id}/mqdefault.jpg'">
      <div class="flex-1 min-w-0">
        <div class="text-xs font-bold text-white truncate">${item.title}</div>
        <div class="text-[10px] text-slate-400 truncate">${item.channel}</div>
      </div>
      ${dur ? `<div class="text-[10px] text-rose-400 font-mono flex-shrink-0">${dur}</div>` : ""}
    `;
    div.addEventListener("click", () => selectSong(item));
    suggestionsDrop.appendChild(div);
  });
  suggestionsDrop.classList.remove("hidden");
}

function selectSong(item) {
  state.selectedSong = item;
  suggestionsDrop.classList.add("hidden");
  songInput.value = item.title;

  selectedThumb.src = item.thumbnail || `https://img.youtube.com/vi/${item.video_id}/mqdefault.jpg`;
  selectedTitle.textContent = item.title;
  selectedChannel.textContent = item.channel;
  selectedDuration.textContent = item.duration ? `Duration: ${formatDuration(item.duration)}` : "";
  selectedCard.classList.remove("hidden");

  generateBtn.disabled = false;
  generateBtnText.textContent = "Launch 3-Agent Pipeline";
  logLine(`Song selected: "${item.title}" by ${item.channel}`, "success");
}

clearBtn.addEventListener("click", () => {
  state.selectedSong = null;
  songInput.value = "";
  selectedCard.classList.add("hidden");
  generateBtn.disabled = true;
  generateBtnText.textContent = "Select a Song First";
});

// ─── VIBE SELECTION ──────────────────────────────────────────────────────────
document.querySelectorAll(".vibe-option").forEach(card => {
  card.addEventListener("click", () => {
    document.querySelectorAll(".vibe-option").forEach(c => c.classList.remove("active"));
    card.classList.add("active");
    state.selectedVibe = card.dataset.v;
  });
});

// ─── PIPELINE EXECUTION ──────────────────────────────────────────────────────
generateBtn.addEventListener("click", async () => {
  if (!state.selectedSong || state.isProcessing) return;
  await runPipeline();
});

async function runPipeline() {
  state.isProcessing = true;
  state.currentRegenSeed = 1;
  resultSection.classList.add("hidden");
  consoleLog.innerHTML = "";
  resetSteps();

  generateBtn.disabled = true;
  generateBtnText.textContent = "Agents Working...";
  pipelineBadge.textContent = "Running";
  pipelineBadge.className = "text-xs font-bold px-3 py-1 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30 animate-pulse";

  const vibe = state.selectedVibe;
  const subtitle = document.getElementById("subtitleStyle").value;

  logLine(`Starting pipeline for: "${state.selectedSong.title}"`, "agent1");
  logLine(`Vibe: ${vibe} | Subtitle: ${subtitle}`, "");

  setStepState(step1, "active");

  try {
    const resp = await fetch("/api/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        youtube_url: state.selectedSong.url,
        song_title: state.selectedSong.title,
        artist: state.selectedSong.channel,
        vibe: vibe,
        subtitle_style: subtitle,
      }),
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Parse SSE events
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";

      for (const rawEvent of events) {
        if (!rawEvent.trim()) continue;
        const eventLine = rawEvent.split("\n").find(l => l.startsWith("event:"));
        const dataLine  = rawEvent.split("\n").find(l => l.startsWith("data:"));
        if (!dataLine) continue;

        const eventType = eventLine ? eventLine.replace("event:", "").trim() : "progress";
        let payload;
        try { payload = JSON.parse(dataLine.replace("data:", "").trim()); }
        catch { continue; }

        const msg = payload.message || "";
        const data = payload.data || {};

        // Determine log colour from message
        let logType = "";
        if (msg.includes("Agent 1")) { logType = "agent1"; setStepState(step1, "active"); }
        else if (msg.includes("Agent 2")) { logType = "agent2"; setStepState(step1, "done"); setStepState(step2, "active"); }
        else if (msg.includes("Agent 3")) { logType = "agent3"; setStepState(step2, "done"); setStepState(step3, "active"); }

        if (eventType === "progress") {
          logLine(msg, logType);
        } else if (eventType === "error") {
          logLine(`ERROR: ${msg}`, "error");
          setStepState(step3, "");
          pipelineBadge.textContent = "Error";
          pipelineBadge.className = "text-xs font-bold px-3 py-1 rounded-full bg-red-500/20 text-red-400 border border-red-500/30";
        } else if (eventType === "complete") {
          logLine(msg, "success");
          setStepState(step3, "done");
          pipelineBadge.textContent = "✓ Ready to Post!";
          pipelineBadge.className = "text-xs font-bold px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
          renderResult(data);
        }
      }
    }

  } catch (err) {
    logLine(`Connection error: ${err.message}`, "error");
    pipelineBadge.textContent = "Error";
  }

  state.isProcessing = false;
  generateBtn.disabled = false;
  generateBtnText.textContent = "Regenerate New Reel";
}

// ─── RENDER RESULTS ───────────────────────────────────────────────────────────
function renderResult(data) {
  resultSection.classList.remove("hidden");
  resultSection.scrollIntoView({ behavior: "smooth", block: "start" });

  const a1 = data.agent1 || {};
  const a2 = data.agent2 || {};
  const a3 = data.agent3 || {};

  // Save scenes for regeneration
  state.currentScenes = a2.scenes || [];
  state.currentVideoUrl = a3.video_url || "";
  state.currentAudioClip = a1.audio_clip || "";

  // Video player
  if (a3.video_url) {
    reelVideo.src = a3.video_url;
    reelVideo.load();
    reelVideo.parentElement.classList.remove("hidden");
    document.getElementById("reelImageSlideshow").classList.add("hidden");
    downloadVideoBtn.onclick = () => {
      const a = document.createElement("a");
      a.href = a3.video_url;
      a.download = "";
      a.click();
    };
  } else {
    // Show image slideshow fallback
    reelVideo.parentElement.classList.add("hidden");
    startSlideshow(state.currentScenes);
  }

  // Audio Hook player
  if (a1.audio_clip) {
    hookAudio.src = a1.audio_clip;
    hookMeta.textContent = `Hook: ${a1.hook_start}s → ${a1.hook_end}s (${a1.hook_duration}s) · Virality: ${a1.virality_score}/100`;
  }

  // Scenes gallery
  renderScenesGallery(state.currentScenes);

  // Caption
  captionText.textContent = a3.full_caption || "";
  postTime.innerHTML = `<i class="fa-regular fa-clock"></i> ${a3.recommended_post_time || ""}`;
}

function renderScenesGallery(scenes) {
  scenesGrid.innerHTML = "";
  scenesCount.textContent = `— ${scenes.length} scenes`;
  scenes.forEach(scene => {
    const card = document.createElement("div");
    card.className = "scene-card";
    if (scene.image_url) {
      card.innerHTML = `
        <img src="${scene.image_url}" alt="Scene ${scene.id}" loading="lazy"
             onerror="this.style.display='none'">
        <div class="scene-label">${scene.text}</div>
      `;
    } else {
      card.innerHTML = `
        <div class="flex items-center justify-center h-full bg-slate-900 text-slate-500 text-xs text-center p-2">${scene.text}</div>
      `;
    }
    scenesGrid.appendChild(card);
  });
}

// ─── IMAGE SLIDESHOW FALLBACK ─────────────────────────────────────────────────
let slideshowInterval = null;
function startSlideshow(scenes) {
  if (slideshowInterval) clearInterval(slideshowInterval);
  if (!scenes.length) return;
  const slideImg = document.getElementById("slideshowImg");
  const slideText = document.getElementById("slideshowText");
  const slideshowEl = document.getElementById("reelImageSlideshow");
  slideshowEl.classList.remove("hidden");
  reelVideo.classList.add("hidden");

  let idx = 0;
  const show = () => {
    const s = scenes[idx % scenes.length];
    if (s.image_url) slideImg.src = s.image_url;
    slideText.textContent = s.text;
    idx++;
  };
  show();
  slideshowInterval = setInterval(show, 5000);
}

// ─── CAPTION COPY ─────────────────────────────────────────────────────────────
copyCaptionBtn.addEventListener("click", () => {
  navigator.clipboard.writeText(captionText.textContent).then(() => {
    copyCaptionBtn.innerHTML = `<i class="fa-solid fa-check text-emerald-400"></i> Copied!`;
    setTimeout(() => {
      copyCaptionBtn.innerHTML = `<i class="fa-regular fa-copy"></i> Copy`;
    }, 2000);
  });
});

// ─── REGENERATE VISUALS ───────────────────────────────────────────────────────
regenerateBtn.addEventListener("click", async () => {
  if (!state.currentScenes.length || state.isProcessing) return;
  state.isProcessing = true;
  state.currentRegenSeed++;
  regenerateBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Generating...`;
  regenerateBtn.disabled = true;

  logLine(`Regenerating visuals (seed: ${state.currentRegenSeed}) with vibe: ${state.selectedVibe}`, "agent2");

  try {
    const resp = await fetch("/api/regenerate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scenes: state.currentScenes.map(s => ({ id: s.id, text: s.text, start: s.start, end: s.end, prompt: s.prompt })),
        audio_clip: state.currentAudioClip,
        vibe: state.selectedVibe,
        song_title: state.selectedSong?.title || "",
        seed: state.currentRegenSeed,
      }),
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const events = buf.split("\n\n");
      buf = events.pop() || "";

      for (const raw of events) {
        const dataLine = raw.split("\n").find(l => l.startsWith("data:"));
        const evtLine  = raw.split("\n").find(l => l.startsWith("event:"));
        if (!dataLine) continue;
        let payload;
        try { payload = JSON.parse(dataLine.replace("data:", "").trim()); }
        catch { continue; }

        const evt = evtLine ? evtLine.replace("event:", "").trim() : "progress";
        logLine(payload.message || "", "agent2");

        if (evt === "complete") {
          state.currentScenes = payload.data?.scenes || state.currentScenes;
          renderScenesGallery(state.currentScenes);
          if (payload.data?.video_url) {
            state.currentVideoUrl = payload.data.video_url;
            reelVideo.src = state.currentVideoUrl;
            reelVideo.load();
            reelVideo.parentElement.classList.remove("hidden");
            document.getElementById("reelImageSlideshow").classList.add("hidden");
            downloadVideoBtn.onclick = () => {
              const a = document.createElement("a");
              a.href = state.currentVideoUrl;
              a.download = "";
              a.click();
            };
          } else if (!state.currentVideoUrl) {
            startSlideshow(state.currentScenes);
          }
          logLine("New visuals generated!", "success");
        }
      }
    }
  } catch (err) {
    logLine(`Regeneration error: ${err.message}`, "error");
  }

  state.isProcessing = false;
  regenerateBtn.innerHTML = `<i class="fa-solid fa-rotate"></i> Regenerate Visuals`;
  regenerateBtn.disabled = false;
});
