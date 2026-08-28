const API_BASE = ""; // same origin as Flask app
const SHARED_TEXT_KEY = "medtermExtractorText";

const state = {
  mode: "original", // "original" | "enhanced"
  selectedFile: null,
};

// ---------------------------- element refs --------------------------------
const modeButtons = document.querySelectorAll(".mode-item");
const modeCaption = document.getElementById("modeCaption");

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const dropzoneTitle = document.getElementById("dropzoneTitle");
const previewImg = document.getElementById("previewImg");
const scanBtn = document.getElementById("scanBtn");
const scanBtnLabel = document.getElementById("scanBtnLabel");
const scanSpinner = document.getElementById("scanSpinner");

const textInput = document.getElementById("textInput");
const evaluateBtn = document.getElementById("evaluateBtn");
const evalBtnLabel = document.getElementById("evalBtnLabel");
const evalSpinner = document.getElementById("evalSpinner");

const resultsContent = document.getElementById("resultsContent");
const resultModeBadge = document.getElementById("resultModeBadge");
const highlightedText = document.getElementById("highlightedText");
const termsTableBody = document.getElementById("termsTableBody");
const confidenceHeader = document.getElementById("confidenceHeader");
const scoreHeader = document.getElementById("scoreHeader");
const noTermsMsg = document.getElementById("noTermsMsg");
const abbrevCol = document.getElementById("abbrevCol");
const abbrevList = document.getElementById("abbrevList");
const errorBanner = document.getElementById("errorBanner");

const savedText = sessionStorage.getItem(SHARED_TEXT_KEY);
if (savedText && !textInput.value.trim()) textInput.value = savedText;

// ------------------------------ mode toggle --------------------------------
const CAPTIONS = {
  original: "Running the <strong>baseline Aho-Corasick</strong> automaton — exact matching only, no context awareness, no fuzzy matching, no abbreviation lookup.",
  enhanced: "Running the <strong>enhanced Aho-Corasick</strong> pipeline — skip-table search, context-aware validation, priority-weighted scoring, abbreviation meanings, and fuzzy matching.",
};

function setMode(mode) {
  state.mode = mode;
  document.body.dataset.mode = mode;
  modeButtons.forEach((btn) => {
    const isActive = btn.dataset.mode === mode;
    btn.classList.toggle("active", isActive);
    btn.setAttribute("aria-selected", String(isActive));
  });
  modeCaption.innerHTML = CAPTIONS[mode];

  // If there's already text (typed or scanned), automatically re-run the
  // analysis under the newly selected mode instead of wiping the results.
  if (textInput.value.trim()) {
    runAnalysis();
  } else {
    hideResults();
  }
}

modeButtons.forEach((btn) => {
  btn.addEventListener("click", () => setMode(btn.dataset.mode));
});

// ------------------------------ file upload --------------------------------
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) handleFile(fileInput.files[0]);
});

["dragover", "dragenter"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

function handleFile(file) {
  if (!file.type.match(/^image\/(jpeg|png|webp)$/)) {
    showError("Unsupported file type. Please upload a JPG, PNG, or WEBP image.");
    return;
  }
  state.selectedFile = file;
  scanBtn.disabled = false;

  const reader = new FileReader();
  reader.onload = (e) => {
    previewImg.src = e.target.result;
    previewImg.hidden = false;
    dropzoneTitle.textContent = file.name;
  };
  reader.readAsDataURL(file);
}

// ------------------------------ Scan & Extract ------------------------------
scanBtn.addEventListener("click", async () => {
  if (!state.selectedFile) return;
  setBusy(scanBtn, scanSpinner, scanBtnLabel, true, "Scanning…");
  clearError();

  const formData = new FormData();
  formData.append("image", state.selectedFile);

  try {
    const res = await fetch(`${API_BASE}/api/ocr`, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "OCR request failed.");
    textInput.value = data.text || "";
    if (textInput.value.trim()) sessionStorage.setItem(SHARED_TEXT_KEY, textInput.value);
    if (textInput.value.trim()) {
      await runAnalysis();
    }
  } catch (err) {
    showError(err.message);
  } finally {
    setBusy(scanBtn, scanSpinner, scanBtnLabel, false, "Scan &amp; Extract");
  }
});

// ------------------------------ Re-evaluate ---------------------------------
evaluateBtn.addEventListener("click", () => runAnalysis());

async function runAnalysis() {
  const text = textInput.value.trim();
  if (!text) {
    showError("Please upload a prescription image or type/paste text first.");
    return;
  }
  clearError();
  sessionStorage.setItem(SHARED_TEXT_KEY, text);
  setBusy(evaluateBtn, evalSpinner, evalBtnLabel, true, "Analyzing…");

  try {
    const res = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, mode: state.mode }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Analysis request failed.");
    renderResults(text, data);
  } catch (err) {
    showError(err.message);
  } finally {
    setBusy(evaluateBtn, evalSpinner, evalBtnLabel, false, "↻ Re-evaluate");
  }
}

// ------------------------------ rendering -----------------------------------
function renderResults(originalText, data) {
  resultsContent.hidden = false;

  const isEnhanced = data.mode === "enhanced";
  resultModeBadge.textContent = isEnhanced ? "ENHANCED" : "ORIGINAL";
  confidenceHeader.hidden = !isEnhanced;
  scoreHeader.hidden = !isEnhanced;
  abbrevCol.hidden = !isEnhanced;

  renderHighlightedText(originalText, data.matches);
  renderTermsTable(data.matches, isEnhanced);

  if (isEnhanced) {
    renderAbbreviations(data.abbreviations || []);
  }

  recordHistoryEntry(originalText, data);
}

function renderHighlightedText(text, matches) {
  if (!matches.length) {
    highlightedText.textContent = text;
    return;
  }
  const sorted = [...matches].sort((a, b) => a.start - b.start);
  let html = "";
  let cursor = 0;
  for (const m of sorted) {
    if (m.start < cursor) continue; // guard against any overlap
    html += escapeHtml(text.slice(cursor, m.start));
    const catClass = categoryClass(m.category);
    const fuzzyClass = m.confidence === "fuzzy" ? " hit-fuzzy" : "";
    const title = m.confidence === "fuzzy"
      ? `Fuzzy match → ${m.matched_dictionary_term}`
      : (m.category || "Medical term");
    html += `<mark class="${catClass}${fuzzyClass}" title="${escapeHtml(title)}">${escapeHtml(text.slice(m.start, m.end))}</mark>`;
    cursor = m.end;
  }
  html += escapeHtml(text.slice(cursor));
  highlightedText.innerHTML = html;
}

function renderTermsTable(matches, isEnhanced) {
  termsTableBody.innerHTML = "";
  noTermsMsg.hidden = matches.length > 0;

  for (const m of matches) {
    const tr = document.createElement("tr");

    const termTd = document.createElement("td");
    termTd.className = "mono";
    const displayedTerm = isEnhanced && m.category === "Symbol"
      ? (m.matched_dictionary_term || m.term)
      : m.term;
    termTd.textContent = displayedTerm;
    tr.appendChild(termTd);

    const catTd = document.createElement("td");
    catTd.textContent = m.category || "—";
    tr.appendChild(catTd);

    if (isEnhanced) {
      const confTd = document.createElement("td");
      const pill = document.createElement("span");
      pill.className = `pill ${m.confidence === "fuzzy" ? "pill-fuzzy" : "pill-exact"}`;
      pill.textContent = m.confidence === "fuzzy" ? "Fuzzy" : "Exact";
      confTd.appendChild(pill);
      tr.appendChild(confTd);

      const scoreTd = document.createElement("td");
      scoreTd.className = "mono";
      scoreTd.textContent = m.score;
      tr.appendChild(scoreTd);
    }

    termsTableBody.appendChild(tr);
  }
}

function renderAbbreviations(abbreviations) {
  abbrevList.innerHTML = "";
  if (!abbreviations.length) {
    const li = document.createElement("li");
    li.textContent = "No abbreviations detected.";
    abbrevList.appendChild(li);
    return;
  }
  for (const a of abbreviations) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="abbrev-term">${escapeHtml(a.term)}</span><span class="abbrev-meaning">${escapeHtml(a.meaning)}</span>`;
    abbrevList.appendChild(li);
  }
}

function categoryClass(category) {
  const map = {
    Drug: "hit-drug",
    Dosage: "hit-dosage",
    Frequency: "hit-frequency",
    Abbreviation: "hit-abbreviation",
    Treatment: "hit-treatment",
  };
  return map[category] || "hit-other";
}

// ------------------------------ utilities -----------------------------------
function setBusy(btn, spinner, label, busy, busyText) {
  btn.disabled = busy || (btn === scanBtn && !state.selectedFile);
  spinner.hidden = !busy;
  label.innerHTML = busy ? busyText : label.dataset.default || label.innerHTML;
  if (!busy && label.dataset.default) label.innerHTML = label.dataset.default;
}

// store default labels once
scanBtnLabel.dataset.default = scanBtnLabel.innerHTML;
evalBtnLabel.dataset.default = evalBtnLabel.innerHTML;

function hideResults() {
  resultsContent.hidden = true;
}

function showError(msg) {
  errorBanner.textContent = msg;
  errorBanner.hidden = false;
}
function clearError() {
  errorBanner.hidden = true;
  errorBanner.textContent = "";
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ------------------------------ scan history --------------------------------
const HISTORY_KEY = "medtermExtractorHistory";
const HISTORY_LIMIT = 50;

function recordHistoryEntry(text, data) {
  try {
    const existing = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    existing.unshift({
      timestamp: new Date().toISOString(),
      mode: data.mode || state.mode,
      text,
      matchCount: (data.matches || []).length,
      terms: (data.matches || []).map((m) => m.term),
    });
    localStorage.setItem(HISTORY_KEY, JSON.stringify(existing.slice(0, HISTORY_LIMIT)));
  } catch (err) {
    // localStorage may be unavailable (e.g. private browsing) — fail silently
    console.warn("Could not save history entry:", err);
  }
}

// init
setMode("original");
