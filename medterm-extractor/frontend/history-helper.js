const ACTIVITY_HISTORY_KEY = "medtermExtractorHistory";
const ACTIVITY_HISTORY_LIMIT = 50;

function saveActivityHistory(entry) {
  if (window.__historyReplay) {
    window.__historyReplay = false;
    return;
  }
  try {
    const existing = JSON.parse(localStorage.getItem(ACTIVITY_HISTORY_KEY) || "[]");
    existing.unshift({
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      timestamp: new Date().toISOString(),
      ...entry,
    });
    localStorage.setItem(
      ACTIVITY_HISTORY_KEY,
      JSON.stringify(existing.slice(0, ACTIVITY_HISTORY_LIMIT)),
    );
  } catch (err) {
    console.warn("Could not save activity history:", err);
  }
}

function consumeActivityHistory(source) {
  const restoreId = sessionStorage.getItem("medtermExtractorHistoryRestore");
  if (!restoreId) return null;

  sessionStorage.removeItem("medtermExtractorHistoryRestore");
  try {
    const entries = JSON.parse(localStorage.getItem(ACTIVITY_HISTORY_KEY) || "[]");
    const entry = entries.find((item) => item.id === restoreId && item.source === source);
    // The main page reruns its analysis during restore and must suppress that
    // automatic run once. SOP pages restore saved DOM state without rerunning.
    if (entry) window.__historyReplay = source === "main";
    return entry || null;
  } catch {
    return null;
  }
}
