const API = (window.PODCAST_API_URL || "").replace(/\/$/, "");
const $ = id => document.getElementById(id);

const fileInput = $("fileInput");
const textInput = $("textInput");
const dropzone = $("dropzone");
let selectedFile = null;
let currentJob = null;

function showError(message){
  $("errorBox").textContent = message;
  $("errorBox").classList.remove("hidden");
}
function clearError(){ $("errorBox").classList.add("hidden"); }

async function api(path, options={}){
  const response = await fetch(`${API}${path}`, options);
  const data = await response.json().catch(() => ({}));
  if(!response.ok) throw new Error(data.detail || `Error ${response.status}`);
  return data;
}

async function checkApi(){
  try{
    const data = await api("/api/health");
    $("apiStatus").textContent = data.status === "ok" ? "API conectada" : "API disponible";
  }catch{
    $("apiStatus").textContent = "API desconectada";
  }
}
checkApi();

$("browseBtn").onclick = () => fileInput.click();
fileInput.onchange = e => selectFile(e.target.files[0]);

function selectFile(file){
  if(!file) return;
  selectedFile = file;
  $("fileName").textContent = `${file.name} · ${(file.size/1024/1024).toFixed(2)} MB`;
  $("fileInfo").classList.remove("hidden");
  textInput.value = "";
  updateCount();
}

$("removeFile").onclick = () => {
  selectedFile = null;
  fileInput.value = "";
  $("fileInfo").classList.add("hidden");
  updateCount();
};

["dragenter","dragover"].forEach(ev => dropzone.addEventListener(ev,e=>{
  e.preventDefault(); dropzone.classList.add("drag");
}));
["dragleave","drop"].forEach(ev => dropzone.addEventListener(ev,e=>{
  e.preventDefault(); dropzone.classList.remove("drag");
}));
dropzone.addEventListener("drop", e => selectFile(e.dataTransfer.files[0]));

function updateCount(){
  $("charCount").textContent = `${textInput.value.length.toLocaleString("es-CL")} caracteres`;
}
textInput.addEventListener("input", updateCount);

$("speed").addEventListener("input", e => $("speedValue").textContent = `${Number(e.target.value).toFixed(2)}×`);

// ============================================================
// SISTEMA DE VOCES
// ============================================================

const KOKORO_VOICES = [
  ["af_heart", "Heart", "Inglés · EE.UU."],
  ["af_alloy", "Alloy", "Inglés · EE.UU."],
  ["af_aoede", "Aoede", "Inglés · EE.UU."],
  ["af_bella", "Bella", "Inglés · EE.UU."],
  ["af_jessica", "Jessica", "Inglés · EE.UU."],
  ["af_kore", "Kore", "Inglés · EE.UU."],
  ["af_nicole", "Nicole", "Inglés · EE.UU."],
  ["af_nova", "Nova", "Inglés · EE.UU."],
  ["af_river", "River", "Inglés · EE.UU."],
  ["af_sarah", "Sarah", "Inglés · EE.UU."],
  ["af_sky", "Sky", "Inglés · EE.UU."],

  ["am_adam", "Adam", "Inglés · EE.UU."],
  ["am_echo", "Echo", "Inglés · EE.UU."],
  ["am_eric", "Eric", "Inglés · EE.UU."],
  ["am_fenrir", "Fenrir", "Inglés · EE.UU."],
  ["am_liam", "Liam", "Inglés · EE.UU."],
  ["am_michael", "Michael", "Inglés · EE.UU."],
  ["am_onyx", "Onyx", "Inglés · EE.UU."],
  ["am_puck", "Puck", "Inglés · EE.UU."],
  ["am_santa", "Santa", "Inglés · EE.UU."],

  ["bf_alice", "Alice", "Inglés · Reino Unido"],
  ["bf_emma", "Emma", "Inglés · Reino Unido"],
  ["bf_isabella", "Isabella", "Inglés · Reino Unido"],
  ["bf_lily", "Lily", "Inglés · Reino Unido"],
  ["bm_daniel", "Daniel", "Inglés · Reino Unido"],
  ["bm_fable", "Fable", "Inglés · Reino Unido"],
  ["bm_george", "George", "Inglés · Reino Unido"],
  ["bm_lewis", "Lewis", "Inglés · Reino Unido"],

  ["ef_dora", "Dora", "Español"],
  ["em_alex", "Alex", "Español"],
  ["em_santa", "Santa", "Español"],

  ["ff_siwis", "Siwis", "Francés"],

  ["hf_alpha", "Alpha", "Hindi"],
  ["hf_beta", "Beta", "Hindi"],
  ["hm_omega", "Omega", "Hindi"],
  ["hm_psi", "Psi", "Hindi"],

  ["if_sara", "Sara", "Italiano"],
  ["im_nicola", "Nicola", "Italiano"],

  ["jf_alpha", "Alpha", "Japonés"],
  ["jf_gongitsune", "Gongitsune", "Japonés"],
  ["jf_nezumi", "Nezumi", "Japonés"],
  ["jf_tebukuro", "Tebukuro", "Japonés"],
  ["jm_kumo", "Kumo", "Japonés"],

  ["pf_dora", "Dora", "Portugués · Brasil"],
  ["pm_alex", "Alex", "Portugués · Brasil"],
  ["pm_santa", "Santa", "Portugués · Brasil"],

  ["zf_xiaobei", "Xiaobei", "Mandarín"],
  ["zf_xiaoni", "Xiaoni", "Mandarín"],
  ["zf_xiaoxiao", "Xiaoxiao", "Mandarín"],
  ["zf_xiaoyi", "Xiaoyi", "Mandarín"],
  ["zm_yunjian", "Yunjian", "Mandarín"],
  ["zm_yunxi", "Yunxi", "Mandarín"],
  ["zm_yunxia", "Yunxia", "Mandarín"],
  ["zm_yunyang", "Yunyang", "Mandarín"]
];

const ELEVENLABS_VOICES = [
  ["EXAVITQu4vr4xnSDxMaL", "Bella", "ElevenLabs"],
  ["21m00Tcm4TlvDq8ikWAM", "Rachel", "ElevenLabs"]
];

function populateVoices(provider, preferredVoice = null) {
  const select = $("voice");

  const voices = provider === "kokoro"
    ? KOKORO_VOICES
    : ELEVENLABS_VOICES;

  select.innerHTML = "";

  voices.forEach(([id, name, language]) => {
    const option = document.createElement("option");
    option.value = id;
    option.textContent = `${name} · ${language}`;
    select.appendChild(option);
  });

  const validPreferred = voices.some(([id]) => id === preferredVoice);

  if (validPreferred) {
    select.value = preferredVoice;
  } else if (provider === "kokoro") {
    select.value = "ef_dora";
  } else {
    select.value = "EXAVITQu4vr4xnSDxMaL";
  }
}

$("provider").addEventListener("change", () => {
  populateVoices($("provider").value);
});

// Kokoro + Dora como configuración inicial
populateVoices("kokoro", "ef_dora");

async function createPodcast(){
  clearError();
  if(!API) return showError("Configura PODCAST_API_URL en frontend/config.js.");

  const btn = $("generateBtn");
  btn.disabled = true;
  $("progressCard").classList.remove("hidden");
  $("playerCard").classList.add("hidden");
  setProgress(2, "Enviando material…");

  try{
    const form = new FormData();
    if(selectedFile) form.append("file", selectedFile);
    if(textInput.value.trim()) form.append("text", textInput.value.trim());
    form.append("profile", $("profile").value);
    form.append("voice", $("voice").value);
    form.append("provider", $("provider").value);
    form.append("speed", $("speed").value);
    form.append("split_chapters", $("splitChapters").checked ? "true" : "false");

    const data = await api("/api/podcasts", {method:"POST", body:form});
    currentJob = data;
    setProgress(10, "Documento preparado…");
    await pollJob(data.job_id);
  }catch(err){
    showError(err.message);
    $("progressCard").classList.add("hidden");
  }finally{
    btn.disabled = false;
  }
}

async function pollJob(jobId){
  for(;;){
    const job = await api(`/api/podcasts/${jobId}`);
    const pct = Math.max(10, Math.min(100, job.progress || 0));
    setProgress(pct, job.message || "Generando audio…");

    if(job.status === "completed"){
      renderResult(job);
      return;
    }
    if(job.status === "failed"){
      throw new Error(job.error || "No se pudo generar el podcast.");
    }
    await new Promise(r => setTimeout(r, 1200));
  }
}

function setProgress(percent, message){
  $("progressBar").style.width = `${percent}%`;
  $("progressPercent").textContent = `${Math.round(percent)}%`;
  $("progressText").textContent = message;
  $("progressTitle").textContent = percent >= 100 ? "Podcast listo" : "Generando tu podcast…";
}

function renderResult(job){
  setProgress(100, "Tu podcast está listo.");
  $("playerCard").classList.remove("hidden");
  $("podcastTitle").textContent = job.title || "Tu podcast";
  $("downloadAll").href = `${API}${job.download_url}`;

  const chapters = $("chapters");
  chapters.innerHTML = "";
  const player = $("audioPlayer");

  job.chapters.forEach((chapter, index) => {
    const row = document.createElement("div");
    row.className = "chapter";
    const play = document.createElement("button");
    play.textContent = "▶";
    play.onclick = () => {
      player.src = `${API}${chapter.audio_url}`;
      $("currentTitle").textContent = chapter.title;
      $("currentMeta").textContent = `${index+1} de ${job.chapters.length}`;
      player.play();
    };
    const middle = document.createElement("div");
    middle.innerHTML = `<strong>${escapeHtml(chapter.title)}</strong><span>${escapeHtml(chapter.characters.toLocaleString("es-CL"))} caracteres</span>`;
    const dl = document.createElement("a");
    dl.className = "secondary";
    dl.href = `${API}${chapter.audio_url}`;
    dl.download = "";
    dl.textContent = "↓";
    row.append(play,middle,dl);
    chapters.appendChild(row);
  });

  if(job.chapters[0]){
    player.src = `${API}${job.chapters[0].audio_url}`;
    $("currentTitle").textContent = job.chapters[0].title;
    $("currentMeta").textContent = `1 de ${job.chapters.length}`;
  }
}

function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
}

$("generateBtn").onclick = createPodcast;
