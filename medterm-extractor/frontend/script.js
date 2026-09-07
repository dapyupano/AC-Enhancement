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

const saveResultBtn = document.getElementById("saveResultBtn");
const saveBtnLabel = document.getElementById("saveBtnLabel");
const saveSpinner = document.getElementById("saveSpinner");
let lastResult = null; // { text, data } from the most recent successful analysis

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
  // Check MIME type OR file extension (some browsers don't recognize HEIC MIME type)
  const validMimeTypes = /^image\/(jpeg|png|webp|heic|heif)$/;
  const validExtensions = /\.(jpg|jpeg|png|webp|heic|heif)$/i;
  
  if (!validMimeTypes.test(file.type) && !validExtensions.test(file.name)) {
    showError("Unsupported file type. Please upload a JPG, PNG, WEBP, or HEIC image.");
    return;
  }
  state.selectedFile = file;
  scanBtn.disabled = false;

  // Browsers can't render HEIC/HEIF natively, so skip preview for those formats
  const isHeic = /\.(heic|heif)$/i.test(file.name) || file.type.match(/^image\/(heic|heif)$/);
  if (isHeic) {
    previewImg.hidden = true;
    dropzoneTitle.textContent = file.name;
    return;
  }

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
  lastResult = { text: originalText, data };

  const isEnhanced = data.mode === "enhanced";
  resultModeBadge.textContent = isEnhanced ? "ENHANCED" : "ORIGINAL";
  categoryHeader.hidden = !isEnhanced;
  confidenceHeader.hidden = !isEnhanced;
  scoreHeader.hidden = !isEnhanced;
  abbrevCol.hidden = !isEnhanced;
  saveResultBtn.hidden = !isEnhanced;

  renderHighlightedText(originalText, data.matches);
  renderTermsTable(data.matches, isEnhanced);

  if (isEnhanced) {
    renderAbbreviations(data.abbreviations || []);
  }

  recordHistoryEntry(originalText, data);
}

function renderHighlightedText(text, matches) {
  highlightedText.textContent = text;
}

function renderTermsTable(matches, isEnhanced) {
  termsTableBody.innerHTML = "";
  noTermsMsg.hidden = matches.length > 0;

  for (const m of matches) {
    const tr = document.createElement("tr");

    const displayTerm = m.matched_dictionary_term || m.term || m.canonical_term || "";
    const termTd = document.createElement("td");
    termTd.className = "mono";
    termTd.textContent = displayTerm;
    tr.appendChild(termTd);

    if (isEnhanced) {
      const catTd = document.createElement("td");
      catTd.textContent = m.category || "—";
      tr.appendChild(catTd);
    }

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

// ------------------------------ save result as PDF --------------------------
saveResultBtn.addEventListener("click", downloadResultPdf);

function downloadResultPdf() {
  if (!lastResult) return;
  if (!window.jspdf || !window.jspdf.jsPDF) {
    showError("PDF library failed to load. Check your connection and try again.");
    return;
  }

  setBusy(saveResultBtn, saveSpinner, saveBtnLabel, true, "Preparing PDF…");

  try {
    const { jsPDF } = window.jspdf;
    const { text, data } = lastResult;
    const isEnhanced = data.mode === "enhanced";
    const matches = data.matches || [];
    const abbreviations = data.abbreviations || [];

    const doc = new jsPDF({ unit: "pt", format: "a4" });
    const margin = 40;
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const maxWidth = pageWidth - margin * 2;
    let y = margin;

    const ensureSpace = (needed) => {
      if (y + needed > pageHeight - margin) {
        doc.addPage();
        y = margin;
      }
    };

    // Title
    doc.setFont("helvetica", "bold");
    doc.setFontSize(16);
    doc.text("Medical Term Extractor — Analysis Result", margin, y);
    y += 18;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(110);
    doc.text(`Mode: ${isEnhanced ? "Enhanced Aho-Corasick" : "Original Aho-Corasick"}`, margin, y);
    y += 12;
    doc.text(`Generated: ${new Date().toLocaleString()}`, margin, y);
    doc.setTextColor(20);
    y += 22;

    // Extracted text
    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    ensureSpace(20);
    doc.text("Extracted Medical Text", margin, y);
    y += 16;

    doc.setFont("courier", "normal");
    doc.setFontSize(9.5);
    const textLines = doc.splitTextToSize(text || "(no text)", maxWidth);
    for (const line of textLines) {
      ensureSpace(12);
      doc.text(line, margin, y);
      y += 12;
    }
    y += 14;

    // Medical terms table
    ensureSpace(24);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.text("Identified Medical Terms", margin, y);
    y += 6;

    const head = isEnhanced
      ? [["Term", "Category", "Confidence", "Score"]]
      : [["Term"]];
    const body = matches.length
      ? matches.map((m) =>
          isEnhanced
            ? [m.term, m.category || "—", m.confidence === "fuzzy" ? "Fuzzy" : "Exact", String(m.score ?? "—")]
            : [m.term]
        )
      : [isEnhanced ? ["—", "No medical terms matched.", "", ""] : ["—"]];

    doc.autoTable({
      startY: y + 6,
      margin: { left: margin, right: margin },
      head,
      body,
      styles: { font: "helvetica", fontSize: 9, cellPadding: 5 },
      headStyles: { fillColor: [15, 157, 120], textColor: 255 },
      alternateRowStyles: { fillColor: [245, 247, 250] },
    });
    y = doc.lastAutoTable.finalY + 24;

    // Abbreviations & symbols panel
    if (isEnhanced) {
      ensureSpace(24);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(12);
      doc.text("Abbreviations & Symbols Panel", margin, y);
      y += 6;

      const abbrevBody = abbreviations.length
        ? abbreviations.map((a) => [a.term, a.meaning])
        : [["—", "No abbreviations detected."]];

      doc.autoTable({
        startY: y + 6,
        margin: { left: margin, right: margin },
        head: [["Term", "Meaning"]],
        body: abbrevBody,
        styles: { font: "helvetica", fontSize: 9, cellPadding: 5 },
        headStyles: { fillColor: [15, 157, 120], textColor: 255 },
        alternateRowStyles: { fillColor: [245, 247, 250] },
      });
    }

    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    doc.save(`medterm-result-${isEnhanced ? "enhanced" : "original"}-${stamp}.pdf`);
  } catch (err) {
    console.error(err);
    showError("Could not generate the PDF. Please try again.");
  } finally {
    setBusy(saveResultBtn, saveSpinner, saveBtnLabel, false, "⬇ Save Result (PDF)");
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
saveBtnLabel.dataset.default = saveBtnLabel.innerHTML;

function hideResults() {
  resultsContent.hidden = true;
  saveResultBtn.hidden = true;
  lastResult = null;
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