const DEFAULT_PLAYBACK_RATE = 0.8;
const DEFAULT_ENGLISH_REPEAT_COUNT = 3;
const EXAMPLE_REPEAT_DELAY_MS = 1500;
const {
  buildClozeCandidates,
  isCorrectClozeAnswer,
  repeatCountForWord,
  sanitizePronunciation,
} = window.EvdLearningHelpers;
const HARD_WORDS_PASSCODE_KEY = "evd-hard-words-passcode";
const HARD_WORDS_LOCAL_KEY = "evd-hard-words-local-state";
const MASTERED_WORDS_LOCAL_KEY = "evd-mastered-words-local-state";
const HARD_WORD_STATUS = {
  active: "active",
  removed: "removed",
};
const MASTERY_STATUS = {
  mastered: "mastered",
  masteredActive: "mastered_active",
};

const state = {
  data: null,
  chapters: [],
  currentChapterIndex: 0,
  currentIndex: 0,
  chapterProgress: {},
  hideMeaning: false,
  repeatAll: true,
  repeatCurrent: false,
  includeExamples: true,
  playbackRate: DEFAULT_PLAYBACK_RATE,
  englishRepeatCount: DEFAULT_ENGLISH_REPEAT_COUNT,
  playbackQueue: [],
  queueIndex: 0,
  isChapterPlayback: false,
  queueTimer: null,
  wakeLock: null,
  wantsWakeLock: false,
  mediaSessionReady: false,
  hardWordsWriteUrl: "",
  hardWordsPending: new Map(),
  masteredWordStatuses: new Map(),
  practice: {
    current: null,
    attempts: 0,
    correct: 0,
  },
};

const elements = {
  chapterTabs: document.getElementById("chapterTabs"),
  wordList: document.getElementById("wordList"),
  categoryText: document.getElementById("categoryText"),
  wordText: document.getElementById("wordText"),
  pronunciationText: document.getElementById("pronunciationText"),
  meaningText: document.getElementById("meaningText"),
  hardWordButton: document.getElementById("hardWordButton"),
  hardWordStatus: document.getElementById("hardWordStatus"),
  masteredWordToggle: document.getElementById("masteredWordToggle"),
  masteredWordStatus: document.getElementById("masteredWordStatus"),
  exampleOneEn: document.getElementById("exampleOneEn"),
  exampleOneZh: document.getElementById("exampleOneZh"),
  exampleTwoEn: document.getElementById("exampleTwoEn"),
  exampleTwoZh: document.getElementById("exampleTwoZh"),
  playButton: document.getElementById("playButton"),
  pauseButton: document.getElementById("pauseButton"),
  previousButton: document.getElementById("previousButton"),
  nextButton: document.getElementById("nextButton"),
  repeatAllToggle: document.getElementById("repeatAllToggle"),
  repeatCurrentToggle: document.getElementById("repeatCurrentToggle"),
  includeExamplesToggle: document.getElementById("includeExamplesToggle"),
  playbackRate: document.getElementById("playbackRate"),
  playbackRateValue: document.getElementById("playbackRateValue"),
  exampleRepeatCount: document.getElementById("exampleRepeatCount"),
  exampleRepeatCountValue: document.getElementById("exampleRepeatCountValue"),
  combinedAudioButton: document.getElementById("combinedAudioButton"),
  toggleMeaningButton: document.getElementById("toggleMeaningButton"),
  audioPlayer: document.getElementById("audioPlayer"),
  practiceScore: document.getElementById("practiceScore"),
  questionMode: document.getElementById("questionMode"),
  questionText: document.getElementById("questionText"),
  questionHint: document.getElementById("questionHint"),
  clozeAnswerInput: document.getElementById("clozeAnswerInput"),
  submitAnswerButton: document.getElementById("submitAnswerButton"),
  answerFeedback: document.getElementById("answerFeedback"),
  nextQuestionButton: document.getElementById("nextQuestionButton"),
};

async function loadDailyData() {
  const candidates = [
    "data/latest.json",
    "../output/data/latest.json",
    "output/data/latest.json",
  ];

  for (const path of candidates) {
    try {
      const response = await fetch(path, { cache: "no-store" });
      if (response.ok) {
        return response.json();
      }
    } catch (error) {
      // Try the next location. This lets the page work from /web or /output.
    }
  }
  throw new Error("Cannot load latest vocabulary data.");
}

function normalizeData(data) {
  if (Array.isArray(data.chapters) && data.chapters.length > 0) {
    return sortHardWordsFirst(data.chapters);
  }
  return sortHardWordsFirst([
    {
      id: "daily",
      title: "Daily",
      word_count: data.words?.length || 0,
      words: data.words || [],
    },
  ]);
}

function sortHardWordsFirst(chapters) {
  return [...chapters].sort((first, second) => (
    Number(Boolean(second.is_hard_words)) - Number(Boolean(first.is_hard_words))
  ));
}

function currentChapter() {
  return state.chapters[state.currentChapterIndex] || { words: [] };
}

function currentWords() {
  return currentChapter().words || [];
}

function currentWord() {
  return currentWords()[state.currentIndex] || {};
}

function render() {
  const chapter = currentChapter();
  const words = currentWords();
  const word = currentWord();
  saveCurrentChapterProgress();
  elements.categoryText.textContent = `${word.category || "Category"} · Difficulty ${word.difficulty || "-"}`;
  elements.wordText.textContent = word.word || "Loading";
  elements.pronunciationText.textContent = sanitizePronunciation(word.pronunciation);
  elements.meaningText.textContent = word.chinese_meaning || "";
  elements.exampleOneEn.textContent = word.example_1_en || "";
  elements.exampleOneZh.textContent = word.example_1_zh || "";
  elements.exampleTwoEn.textContent = word.example_2_en || "";
  elements.exampleTwoZh.textContent = word.example_2_zh || "";
  elements.combinedAudioButton.textContent = `播放 ${chapter.title || "本章節"}`;

  document.body.classList.toggle("hidden-meaning", state.hideMeaning);
  renderChapterTabs();
  renderWordList();
  updateHardWordControls();
  updateMasteredControls();
  saveProgress();
}

function renderChapterTabs() {
  elements.chapterTabs.innerHTML = "";
  state.chapters.forEach((chapter, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `chapter-tab${index === state.currentChapterIndex ? " active" : ""}`;
    button.textContent = `${chapter.title || `Chapter ${index + 1}`} (${chapterProgressText(chapter, index)})`;
    button.addEventListener("click", () => {
      stopQueue();
      saveCurrentChapterProgress();
      state.currentChapterIndex = index;
      state.currentIndex = Math.max(0, savedChapterIndex(chapter));
      render();
      buildQuestion();
    });
    elements.chapterTabs.appendChild(button);
  });
}

function chapterWordCount(chapter) {
  const words = chapter.words || [];
  if (chapter.is_hard_words) {
    return words.length;
  }
  return chapter.word_count || words.length;
}

function chapterProgressText(chapter, index) {
  const total = chapterWordCount(chapter);
  if (total <= 0) {
    return "0/0";
  }
  if (index === state.currentChapterIndex) {
    return `${Math.min(state.currentIndex + 1, total)}/${total}`;
  }
  const savedIndex = savedChapterIndex(chapter);
  return savedIndex >= 0 ? `${Math.min(savedIndex + 1, total)}/${total}` : `0/${total}`;
}

function chapterKey(chapter) {
  return chapter.id || chapter.source_file || chapter.title || "";
}

function savedChapterIndex(chapter) {
  const key = chapterKey(chapter);
  if (!key || state.chapterProgress[key] === undefined) {
    return -1;
  }
  return Math.min(Number(state.chapterProgress[key]) || 0, Math.max(0, chapterWordCount(chapter) - 1));
}

function saveCurrentChapterProgress() {
  const chapter = currentChapter();
  const key = chapterKey(chapter);
  if (key && chapterWordCount(chapter) > 0) {
    state.chapterProgress[key] = state.currentIndex;
  }
}

function renderWordList() {
  elements.wordList.innerHTML = "";
  currentWords().forEach((word, index) => {
    const button = document.createElement("button");
    button.type = "button";
    const masteredClass = isMasteredWord(word) ? "word-item mastered" : "word-item";
    button.className = `${masteredClass}${index === state.currentIndex ? " active" : ""}`;
    button.innerHTML = `<strong>${index + 1}. ${escapeHtml(word.word)}</strong><small>${escapeHtml(word.chinese_meaning)}</small>`;
    button.addEventListener("click", () => {
      stopQueue();
      state.currentIndex = index;
      render();
      playCurrent();
    });
    elements.wordList.appendChild(button);
  });
  scrollActiveWordIntoView();
}

function scrollActiveWordIntoView() {
  const container = elements.wordList;
  const activeButton = container.querySelector(".word-item.active");
  if (!activeButton) {
    return;
  }
  const containerRect = container.getBoundingClientRect();
  const activeRect = activeButton.getBoundingClientRect();
  const targetTop = container.scrollTop + activeRect.top - containerRect.top
    - container.clientHeight / 2 + activeButton.clientHeight / 2;
  container.scrollTop = Math.max(0, targetTop);
}

function playCurrent() {
  const word = currentWord();
  const queue = buildWordQueue(word);
  if (queue.length === 0 && word.audio) {
    playDirectAudio(word.audio, true);
    return;
  }
  playQueue(queue, false);
}

function playCombinedAudio() {
  const chapterQueue = buildChapterQueue();
  if (chapterQueue.length > 0) {
    playQueue(chapterQueue, true);
    return;
  }
  if (state.data.combined_audio) {
    playDirectAudio(state.data.combined_audio, true);
  }
}

function buildChapterQueue() {
  return currentWords().flatMap((word) => buildWordQueue(word));
}

function buildWordQueue(word) {
  const segments = word?.audio_segments || {};
  const queue = [];
  const repeatCount = repeatCountForWord(isMasteredWord(word), state.englishRepeatCount);
  addRepeatedEnglishWithChinese(queue, segments.word, word?.word, segments.meaning, word?.chinese_meaning, repeatCount);
  if (state.includeExamples) {
    addRepeatedEnglishWithChinese(queue, segments.example_1_en, word?.example_1_en, segments.example_1_zh, word?.example_1_zh, repeatCount);
    addRepeatedEnglishWithChinese(queue, segments.example_2_en, word?.example_2_en, segments.example_2_zh, word?.example_2_zh, repeatCount);
  }
  return queue;
}

function addRepeatedEnglishWithChinese(
  queue,
  englishSegment,
  englishText,
  chineseSegment,
  chineseText,
  repeatCount,
) {
  addNarration(queue, englishSegment, englishText, "en");
  addNarration(queue, chineseSegment, chineseText, "zh");
  for (let count = 1; count < repeatCount; count += 1) {
    addNarration(queue, englishSegment, englishText, "en", EXAMPLE_REPEAT_DELAY_MS);
  }
}

function addNarration(queue, segment, fallbackText, fallbackLanguage, delayMs = 0) {
  if (segment?.src) {
    queue.push({
      src: segment.src,
      language: segment.language || fallbackLanguage,
      delayMs,
    });
    return;
  }
  if (!fallbackText) {
    return;
  }
  queue.push({
    text: fallbackText,
    language: fallbackLanguage,
    delayMs,
  });
}

function playQueue(queue, isChapterPlayback) {
  if (queue.length === 0) {
    showPlaybackError("目前沒有可播放的音訊。");
    return;
  }
  stopQueue();
  state.playbackQueue = queue;
  state.queueIndex = 0;
  state.isChapterPlayback = isChapterPlayback;
  requestWakeLock();
  updateMediaSession();
  playNextQueueSegment();
}

function playNextQueueSegment() {
  const segment = state.playbackQueue[state.queueIndex];
  if (!segment) {
    finishQueue();
    return;
  }
  state.queueIndex += 1;
  updateMediaSession();
  const startSegment = () => {
    if (!segment.src && segment.text) {
      speakTextSegment(segment);
      return;
    }
    elements.audioPlayer.src = resolveAssetPath(segment.src);
    applyPlaybackRate(segment);
    elements.audioPlayer.play().catch(() => {
      showPlaybackError("瀏覽器無法播放這段音訊。");
    });
  };
  if (segment.delayMs > 0) {
    state.queueTimer = window.setTimeout(startSegment, segment.delayMs);
  } else {
    startSegment();
  }
}

function speakTextSegment(segment) {
  if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) {
    showPlaybackError("瀏覽器不支援線上語音朗讀。");
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(speechTextForAudio(segment.text, segment.language));
  utterance.lang = segment.language === "zh" ? "zh-TW" : "en-US";
  utterance.rate = segment.language === "en" ? state.playbackRate : 1;
  utterance.onend = playNextQueueSegment;
  utterance.onerror = () => showPlaybackError("瀏覽器語音朗讀失敗。");
  window.speechSynthesis.speak(utterance);
}

function speechTextForAudio(text, language) {
  const value = String(text || "");
  if (language === "zh") {
    return value.replaceAll("地", "第");
  }
  return expandKnownAbbreviationsForSpeech(value);
}

function expandKnownAbbreviationsForSpeech(text) {
  return text
    .replaceAll(/\bMilitary Standard 461 \(MIL-STD-461\)|\bMIL-STD-461\b/g, "Military Standard 461")
    .replaceAll(/\bElectromagnetic Compatibility \(EMC\)|\bEMC\b/g, "Electromagnetic Compatibility")
    .replaceAll(/\bElectromagnetic Susceptibility \(EMS\)|\bEMS\b/g, "Electromagnetic Susceptibility")
    .replaceAll(/\bElectromagnetic Environmental Effects \(E3\)|\bE3\b/g, "Electromagnetic Environmental Effects")
    .replaceAll(/\bElectronic Power Distribution System \(EPDS\)|\bEPDS\b/g, "Electronic Power Distribution System");
}

function updateHardWordControls() {
  if (!elements.hardWordButton || !elements.hardWordStatus) {
    return;
  }
  if (!state.hardWordsWriteUrl) {
    elements.hardWordButton.hidden = true;
    elements.hardWordStatus.textContent = "";
    return;
  }
  const word = currentWord();
  const wordKey = hardWordKey(word);
  const alreadyAdded = isHardWord(wordKey);
  const mastered = isMasteredWord(word);
  elements.hardWordButton.hidden = false;
  elements.hardWordButton.disabled = !word.word || mastered;
  elements.hardWordButton.textContent = alreadyAdded ? "從未熟記單字移除" : "加入未熟記單字練習";
  elements.hardWordStatus.textContent = mastered
    ? "已熟記，取消勾選後可加入未熟記練習"
    : alreadyAdded ? "目前在未熟記單字練習" : "";
}

function masteryStatus(word) {
  return state.masteredWordStatuses.get(hardWordKey(word)) || "";
}

function isMasteredWord(word) {
  const status = masteryStatus(word);
  return status === MASTERY_STATUS.mastered || status === MASTERY_STATUS.masteredActive;
}

function updateMasteredControls() {
  if (!elements.masteredWordToggle || !elements.masteredWordStatus) {
    return;
  }
  const word = currentWord();
  elements.masteredWordToggle.checked = isMasteredWord(word);
  elements.masteredWordToggle.disabled = !word.word || !state.hardWordsWriteUrl;
  elements.masteredWordStatus.textContent = isMasteredWord(word) ? "英文播放一次" : "";
}

function isHardWord(wordKey) {
  if (!wordKey) {
    return false;
  }
  if (state.hardWordsPending.has(wordKey)) {
    return state.hardWordsPending.get(wordKey);
  }
  return state.chapters.some((chapter) => (
    chapter.is_hard_words
    && (chapter.words || []).some((word) => hardWordKey(word) === wordKey)
  ));
}

function hardWordKey(word) {
  return String(word?.word || "").trim().toLowerCase();
}

function hardWordsChapter() {
  return state.chapters.find((chapter) => chapter.is_hard_words);
}

function ensureHardWordsChapter() {
  let chapter = hardWordsChapter();
  if (!chapter) {
    chapter = {
      id: "hard-words",
      title: "未熟記單字練習",
      source_file: "hard_words.csv",
      is_hard_words: true,
      word_count: 0,
      words: [],
    };
    state.chapters.unshift(chapter);
  }
  return chapter;
}

function applyHardWordLocalState(word, status) {
  const chapter = ensureHardWordsChapter();
  const wordKey = hardWordKey(word);
  if (!wordKey) {
    return;
  }
  chapter.words = chapter.words || [];
  const existingIndex = chapter.words.findIndex((item) => hardWordKey(item) === wordKey);
  if (status === HARD_WORD_STATUS.active && existingIndex === -1) {
    chapter.words.unshift({ ...word });
  } else if (status === HARD_WORD_STATUS.removed && existingIndex !== -1) {
    chapter.words.splice(existingIndex, 1);
    if (currentChapter() === chapter) {
      state.currentIndex = Math.min(state.currentIndex, Math.max(0, chapter.words.length - 1));
    }
  }
  chapter.word_count = chapter.words.length;
}

function readHardWordsLocalState() {
  const empty = { active: [], removed: [] };
  const raw = localStorage.getItem(HARD_WORDS_LOCAL_KEY);
  if (!raw) {
    return empty;
  }
  try {
    const saved = JSON.parse(raw);
    return {
      active: Array.isArray(saved.active) ? saved.active : [],
      removed: Array.isArray(saved.removed) ? saved.removed : [],
    };
  } catch (error) {
    localStorage.removeItem(HARD_WORDS_LOCAL_KEY);
    return empty;
  }
}

function saveHardWordsLocalState(word, status) {
  const wordKey = hardWordKey(word);
  if (!wordKey) {
    return;
  }
  const saved = readHardWordsLocalState();
  saved.active = saved.active.filter((savedWord) => hardWordKey(savedWord) !== wordKey);
  saved.removed = saved.removed.filter((savedWordKey) => savedWordKey !== wordKey);
  if (status === HARD_WORD_STATUS.active) {
    saved.active.unshift({ ...word });
  } else if (status === HARD_WORD_STATUS.removed) {
    saved.removed.push(wordKey);
  }
  localStorage.setItem(HARD_WORDS_LOCAL_KEY, JSON.stringify(saved));
}

function restoreHardWordsLocalState() {
  const saved = readHardWordsLocalState();
  saved.removed.forEach((wordKey) => applyHardWordLocalState({ word: wordKey }, HARD_WORD_STATUS.removed));
  saved.active.slice().reverse().forEach(
    (savedWord) => applyHardWordLocalState(savedWord, HARD_WORD_STATUS.active),
  );
  const chapter = hardWordsChapter();
  if (chapter) {
    chapter.word_count = (chapter.words || []).length;
  }
}

function readMasteredLocalState() {
  const raw = localStorage.getItem(MASTERED_WORDS_LOCAL_KEY);
  if (!raw) {
    return {};
  }
  try {
    const saved = JSON.parse(raw);
    return saved && typeof saved === "object" && !Array.isArray(saved) ? saved : {};
  } catch (error) {
    localStorage.removeItem(MASTERED_WORDS_LOCAL_KEY);
    return {};
  }
}

function saveMasteredLocalState(word, status) {
  const wordKey = hardWordKey(word);
  if (!wordKey) {
    return;
  }
  const saved = readMasteredLocalState();
  saved[wordKey] = status;
  localStorage.setItem(MASTERED_WORDS_LOCAL_KEY, JSON.stringify(saved));
}

function restoreMasteredLocalState() {
  Object.entries(readMasteredLocalState()).forEach(([wordKey, status]) => {
    state.masteredWordStatuses.set(wordKey, status);
  });
}

async function toggleMasteredWord() {
  if (!state.hardWordsWriteUrl) {
    return;
  }
  const word = currentWord();
  const wordKey = hardWordKey(word);
  if (!wordKey) {
    return;
  }
  const currentStatus = masteryStatus(word);
  const wasHardWord = isHardWord(wordKey);
  const nextStatus = elements.masteredWordToggle.checked
    ? (wasHardWord ? MASTERY_STATUS.masteredActive : MASTERY_STATUS.mastered)
    : (currentStatus === MASTERY_STATUS.masteredActive ? HARD_WORD_STATUS.active : HARD_WORD_STATUS.removed);
  const passcode = getHardWordsPasscode();
  if (!passcode) {
    elements.masteredWordToggle.checked = isMasteredWord(word);
    elements.masteredWordStatus.textContent = "未設定同步密碼";
    return;
  }

  elements.masteredWordToggle.disabled = true;
  elements.masteredWordStatus.textContent = "同步中...";
  try {
    await postHardWord(word, passcode, nextStatus);
    state.masteredWordStatuses.set(wordKey, nextStatus);
    saveMasteredLocalState(word, nextStatus);
    if (nextStatus === MASTERY_STATUS.masteredActive) {
      state.hardWordsPending.set(wordKey, false);
      saveHardWordsLocalState(word, HARD_WORD_STATUS.removed);
      applyHardWordLocalState(word, HARD_WORD_STATUS.removed);
    } else if (nextStatus === HARD_WORD_STATUS.active) {
      state.hardWordsPending.set(wordKey, true);
      saveHardWordsLocalState(word, HARD_WORD_STATUS.active);
      applyHardWordLocalState(word, HARD_WORD_STATUS.active);
    }
    render();
  } catch (error) {
    elements.masteredWordToggle.disabled = false;
    elements.masteredWordToggle.checked = isMasteredWord(word);
    elements.masteredWordStatus.textContent = "同步失敗，請稍後再試";
  }
}

async function toggleHardWord() {
  if (!state.hardWordsWriteUrl) {
    return;
  }
  const word = currentWord();
  const wordKey = hardWordKey(word);
  if (!wordKey) {
    updateHardWordControls();
    return;
  }
  const nextStatus = isHardWord(wordKey) ? HARD_WORD_STATUS.removed : HARD_WORD_STATUS.active;
  const passcode = getHardWordsPasscode();
  if (!passcode) {
    elements.hardWordStatus.textContent = "未設定同步密碼";
    return;
  }

  elements.hardWordButton.disabled = true;
  elements.hardWordStatus.textContent = "同步中...";
  try {
    await postHardWord(word, passcode, nextStatus);
    state.hardWordsPending.set(wordKey, nextStatus === HARD_WORD_STATUS.active);
    saveHardWordsLocalState(word, nextStatus);
    applyHardWordLocalState(word, nextStatus);
    render();
    elements.hardWordStatus.textContent = nextStatus === HARD_WORD_STATUS.active
      ? "已加入未熟記單字練習"
      : "已從未熟記單字移除";
  } catch (error) {
    elements.hardWordButton.disabled = false;
    elements.hardWordStatus.textContent = "同步失敗，請稍後再試";
  }
}

function getHardWordsPasscode() {
  const saved = localStorage.getItem(HARD_WORDS_PASSCODE_KEY);
  if (saved) {
    return saved;
  }
  const entered = window.prompt("請輸入未熟記單字同步密碼");
  if (!entered) {
    return "";
  }
  localStorage.setItem(HARD_WORDS_PASSCODE_KEY, entered);
  return entered;
}

async function postHardWord(word, passcode, status) {
  const chapter = currentChapter();
  const payload = {
    passcode,
    "status": status,
    added_at: new Date().toISOString(),
    source_chapter: chapter.title || "",
    source_id: word.id || "",
    id: word.id || "",
    word: word.word || "",
    pronunciation: word.pronunciation || "",
    chinese_meaning: word.chinese_meaning || "",
    example_1_en: word.example_1_en || "",
    example_1_zh: word.example_1_zh || "",
    example_2_en: word.example_2_en || "",
    example_2_zh: word.example_2_zh || "",
    category: word.category || "",
    difficulty: word.difficulty || "",
    review_count: word.review_count || "0",
    last_review_date: word.last_review_date || "",
  };
  const response = await fetch(state.hardWordsWriteUrl, {
    method: "POST",
    mode: "no-cors",
    headers: {
      "Content-Type": "text/plain;charset=utf-8",
    },
    body: JSON.stringify(payload),
  });
  if (response.type !== "opaque" && !response.ok) {
    throw new Error("Hard words sync failed.");
  }
}

function finishQueue() {
  if (state.isChapterPlayback) {
    state.isChapterPlayback = false;
    releaseWakeLock();
    updateMediaSessionPlaybackState("none");
    return;
  }
  if (state.repeatCurrent) {
    playCurrent();
    return;
  }
  nextWord(state.repeatAll);
}

function stopQueue() {
  if (state.queueTimer) {
    window.clearTimeout(state.queueTimer);
    state.queueTimer = null;
  }
  state.playbackQueue = [];
  state.queueIndex = 0;
  state.isChapterPlayback = false;
  state.wantsWakeLock = false;
  releaseWakeLock();
  updateMediaSessionPlaybackState("none");
  elements.audioPlayer.pause();
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}

function playDirectAudio(src, language) {
  stopQueue();
  const playbackLanguage = language === true ? "en" : language === false ? "zh" : language;
  elements.audioPlayer.src = resolveAssetPath(src);
  applyPlaybackRate({ language: playbackLanguage || "en" });
  requestWakeLock();
  updateMediaSession();
  elements.audioPlayer.play().catch(() => {
    showPlaybackError("瀏覽器無法播放音訊。");
  });
}

async function requestWakeLock() {
  state.wantsWakeLock = true;
  if (!("wakeLock" in navigator) || state.wakeLock) {
    return;
  }
  try {
    state.wakeLock = await navigator.wakeLock.request("screen");
    state.wakeLock.addEventListener("release", () => {
      state.wakeLock = null;
    });
  } catch (error) {
    state.wakeLock = null;
  }
}

function releaseWakeLock() {
  state.wantsWakeLock = false;
  if (!state.wakeLock) {
    return;
  }
  state.wakeLock.release().catch(() => {});
  state.wakeLock = null;
}

function setupMediaSession() {
  if (!("mediaSession" in navigator) || state.mediaSessionReady) {
    return;
  }
  state.mediaSessionReady = true;
  navigator.mediaSession.setActionHandler("play", () => {
    if (elements.audioPlayer.src && elements.audioPlayer.paused) {
      requestWakeLock();
      elements.audioPlayer.play();
      return;
    }
    playCurrent();
  });
  navigator.mediaSession.setActionHandler("pause", pausePlayback);
  navigator.mediaSession.setActionHandler("nexttrack", () => {
    stopQueue();
    nextWord(true);
  });
  navigator.mediaSession.setActionHandler("previoustrack", () => {
    stopQueue();
    previousWord();
    playCurrent();
  });
}

function updateMediaSession() {
  if (!("mediaSession" in navigator) || !("MediaMetadata" in window)) {
    return;
  }
  const chapter = currentChapter();
  const word = currentWord();
  navigator.mediaSession.metadata = new MediaMetadata({
    title: word.word || "EVD Vocabulary",
    artist: word.chinese_meaning || chapter.title || "",
    album: chapter.title || "EVD Vocabulary",
  });
  updateMediaSessionPlaybackState("playing");
}

function updateMediaSessionPlaybackState(playbackState) {
  if ("mediaSession" in navigator) {
    navigator.mediaSession.playbackState = playbackState;
  }
}

function pausePlayback() {
  if (state.queueTimer) {
    window.clearTimeout(state.queueTimer);
    state.queueTimer = null;
  }
  elements.audioPlayer.pause();
  if (window.speechSynthesis) {
    window.speechSynthesis.pause();
  }
  releaseWakeLock();
  updateMediaSessionPlaybackState("paused");
}

function nextWord(autoplay = false) {
  const words = currentWords();
  const lastIndex = words.length - 1;
  if (state.currentIndex >= lastIndex) {
    if (!state.repeatAll) {
      return;
    }
    state.currentIndex = 0;
  } else {
    state.currentIndex += 1;
  }
  render();
  if (autoplay) {
    playCurrent();
  }
}

function previousWord() {
  const lastIndex = currentWords().length - 1;
  if (lastIndex < 0) {
    return;
  }
  state.currentIndex = state.currentIndex === 0 ? lastIndex : state.currentIndex - 1;
  render();
}

function resolveAssetPath(path) {
  if (!path) {
    return "";
  }
  const normalized = path.replaceAll("\\", "/");
  if (window.location.pathname.includes("/output/") && normalized.startsWith("output/")) {
    return normalized.replace(/^output\//, "");
  }
  if (window.location.pathname.includes("/web/") && normalized.startsWith("output/")) {
    return `../${normalized}`;
  }
  return normalized;
}

function buildQuestion() {
  const candidates = buildClozeCandidates(currentWords());
  if (candidates.length === 0) {
    state.practice.current = null;
    elements.questionMode.textContent = "英文例句填空";
    elements.questionText.textContent = "本章節沒有可用的填空例句";
    elements.questionHint.textContent = "";
    elements.clozeAnswerInput.value = "";
    elements.clozeAnswerInput.disabled = true;
    elements.submitAnswerButton.disabled = true;
    elements.answerFeedback.textContent = "";
    return;
  }
  const candidate = candidates[Math.floor(Math.random() * candidates.length)];
  state.practice.current = {
    word: candidate.word,
    correctAnswer: candidate.answer,
  };
  elements.questionMode.textContent = "請依中文提示填空";
  elements.questionText.textContent = candidate.clozeText;
  elements.questionHint.textContent = candidate.hint;
  elements.answerFeedback.textContent = "";
  elements.answerFeedback.className = "feedback";
  elements.clozeAnswerInput.value = "";
  elements.clozeAnswerInput.disabled = false;
  elements.submitAnswerButton.disabled = false;
}

function answerQuestion(answer) {
  const current = state.practice.current;
  if (!current) {
    return;
  }
  state.practice.attempts += 1;
  if (isCorrectClozeAnswer(answer, current.correctAnswer)) {
    state.practice.correct += 1;
    elements.answerFeedback.textContent = "答對";
    elements.answerFeedback.className = "feedback correct";
  } else {
    elements.answerFeedback.textContent = `答錯，答案是 ${current.correctAnswer}`;
    elements.answerFeedback.className = "feedback wrong";
  }
  elements.clozeAnswerInput.disabled = true;
  elements.submitAnswerButton.disabled = true;
  updatePracticeScore();
  saveProgress();
}

function submitCurrentAnswer() {
  answerQuestion(elements.clozeAnswerInput.value);
}

function updatePracticeScore() {
  elements.practiceScore.textContent = `${state.practice.correct} / ${state.practice.attempts}`;
}

function applyPlaybackRate(segment = currentQueueSegment()) {
  const rate = segment.language === "en" ? state.playbackRate : 1;
  elements.audioPlayer.playbackRate = rate;
  elements.playbackRate.value = String(state.playbackRate);
  elements.playbackRateValue.textContent = `${state.playbackRate.toFixed(1)}x`;
  elements.exampleRepeatCount.value = String(state.englishRepeatCount);
  elements.exampleRepeatCountValue.textContent = String(state.englishRepeatCount);
  elements.includeExamplesToggle.checked = state.includeExamples;
}

function currentQueueSegment() {
  return state.playbackQueue[Math.max(0, state.queueIndex - 1)] || { language: "en" };
}

function showPlaybackError(message) {
  elements.answerFeedback.textContent = message;
  elements.answerFeedback.className = "feedback wrong";
}

function saveProgress() {
  if (!state.data) {
    return;
  }
  const key = `evd-progress-${state.data.date}`;
  localStorage.setItem(
    key,
    JSON.stringify({
      currentChapterIndex: state.currentChapterIndex,
      currentIndex: state.currentIndex,
      chapterProgress: state.chapterProgress,
      playbackRate: state.playbackRate,
      englishRepeatCount: state.englishRepeatCount,
      includeExamples: state.includeExamples,
      practice: state.practice,
    }),
  );
}

function restoreProgress() {
  const key = `evd-progress-${state.data.date}`;
  const raw = localStorage.getItem(key);
  if (!raw) {
    return;
  }
  try {
    const saved = JSON.parse(raw);
    state.currentChapterIndex = Math.min(saved.currentChapterIndex || 0, state.chapters.length - 1);
    state.currentIndex = Math.max(0, Math.min(saved.currentIndex || 0, currentWords().length - 1));
    state.chapterProgress = saved.chapterProgress || {};
    state.playbackRate = Number(saved.playbackRate || DEFAULT_PLAYBACK_RATE);
    state.englishRepeatCount = clampRepeatCount(saved.englishRepeatCount || saved.exampleRepeatCount || DEFAULT_ENGLISH_REPEAT_COUNT);
    state.includeExamples = saved.includeExamples !== false;
    state.practice.attempts = saved.practice?.attempts || 0;
    state.practice.correct = saved.practice?.correct || 0;
  } catch (error) {
    localStorage.removeItem(key);
  }
}

function clampRepeatCount(value) {
  return Math.min(5, Math.max(1, Number(value) || DEFAULT_ENGLISH_REPEAT_COUNT));
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

elements.playButton.addEventListener("click", playCurrent);
elements.pauseButton.addEventListener("click", pausePlayback);
elements.nextButton.addEventListener("click", () => {
  stopQueue();
  nextWord(false);
});
elements.previousButton.addEventListener("click", () => {
  stopQueue();
  previousWord();
});
elements.combinedAudioButton.addEventListener("click", playCombinedAudio);
elements.repeatAllToggle.addEventListener("change", (event) => {
  state.repeatAll = event.target.checked;
});
elements.repeatCurrentToggle.addEventListener("change", (event) => {
  state.repeatCurrent = event.target.checked;
});
elements.includeExamplesToggle.addEventListener("change", (event) => {
  state.includeExamples = event.target.checked;
  saveProgress();
});
elements.playbackRate.addEventListener("input", (event) => {
  state.playbackRate = Number(event.target.value);
  applyPlaybackRate();
  saveProgress();
});
elements.exampleRepeatCount.addEventListener("input", (event) => {
  state.englishRepeatCount = clampRepeatCount(event.target.value);
  applyPlaybackRate();
  saveProgress();
});
elements.toggleMeaningButton.addEventListener("click", () => {
  state.hideMeaning = !state.hideMeaning;
  elements.toggleMeaningButton.textContent = state.hideMeaning ? "顯示中文" : "隱藏中文";
  render();
});
elements.nextQuestionButton.addEventListener("click", buildQuestion);
elements.submitAnswerButton.addEventListener("click", submitCurrentAnswer);
elements.clozeAnswerInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !elements.submitAnswerButton.disabled) {
    submitCurrentAnswer();
  }
});
elements.hardWordButton.addEventListener("click", toggleHardWord);
elements.masteredWordToggle.addEventListener("change", toggleMasteredWord);
elements.audioPlayer.addEventListener("ended", playNextQueueSegment);
elements.audioPlayer.addEventListener("loadedmetadata", () => applyPlaybackRate());
elements.audioPlayer.addEventListener("play", () => applyPlaybackRate());
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && state.wantsWakeLock) {
    requestWakeLock();
  }
});

loadDailyData()
  .then((data) => {
    state.data = data;
    state.chapters = normalizeData(data);
    state.hardWordsWriteUrl = data.hard_words?.write_url || "";
    Object.entries(data.mastery?.statuses || {}).forEach(([wordKey, status]) => {
      state.masteredWordStatuses.set(hardWordKey({ word: wordKey }), status);
    });
    restoreHardWordsLocalState();
    restoreMasteredLocalState();
    restoreProgress();
    setupMediaSession();
    applyPlaybackRate();
    render();
    buildQuestion();
    updatePracticeScore();
  })
  .catch((error) => {
    elements.wordText.textContent = "無法載入單字資料";
    elements.meaningText.textContent = error.message;
  });
