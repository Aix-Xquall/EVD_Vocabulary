const DEFAULT_PLAYBACK_RATE = 1.0;
const DEFAULT_ENGLISH_REPEAT_COUNT = 5;
const ENGLISH_REPEAT_DELAY_MS = 1500;
const EXAMPLE_GROUP_DELAY_MS = 2000;
const WORD_GROUP_DELAY_MS = 2000;
const REPEAT_CURRENT_DELAY_MS = 1500;
const {
  buildClozeCandidates,
  buildSuggestionSegments,
  describePluralAnswerRequirement,
  findClosestVocabularyMatch,
  findLiteralHighlightRanges,
  findTargetPhraseMatches,
  findVocabularySource,
  incrementPracticeRecord,
  isCorrectClozeAnswer,
  repeatCountForWord,
  sanitizePronunciation,
} = window.EvdLearningHelpers;
const HARD_WORDS_PASSCODE_KEY = "evd-hard-words-passcode";
const HARD_WORDS_LOCAL_KEY = "evd-hard-words-local-state";
const MASTERED_WORDS_LOCAL_KEY = "evd-mastered-words-local-state";
const PRACTICE_STATS_LOCAL_KEY = "evd-practice-stats-v1";
const PRACTICE_STATS_SENTINEL_WORD = "__EVD_PRACTICE_STATS__";
const PRACTICE_STATS_SYNC_DELAY_MS = 60000;
const PRACTICE_STATS_MIN_SYNC_INTERVAL_MS = 300000;
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
  isPaused: false,
  pausedQueueIndex: 0,
  isChapterPlayback: false,
  queueTimer: null,
  wakeLock: null,
  wantsWakeLock: false,
  mediaSessionReady: false,
  hardWordsWriteUrl: "",
  hardWordsPending: new Map(),
  masteredWordStatuses: new Map(),
  practiceStats: new Map(),
  practiceStatsView: "frequent",
  practiceStatsDirty: false,
  practiceStatsSyncTimer: null,
  practiceStatsLastSyncAt: 0,
  practiceSettingsUpdatedAt: "",
  directPlayback: null,
  practice: {
    current: null,
    attempts: 0,
    correct: 0,
  },
};

const elements = {
  chapterSelect: document.getElementById("chapterSelect"),
  wordList: document.getElementById("wordList"),
  categoryText: document.getElementById("categoryText"),
  wordText: document.getElementById("wordText"),
  pronunciationText: document.getElementById("pronunciationText"),
  meaningText: document.getElementById("meaningText"),
  currentWordStats: document.getElementById("currentWordStats"),
  hardWordButton: document.getElementById("hardWordButton"),
  hardWordHelp: document.getElementById("hardWordHelp"),
  hardWordStatus: document.getElementById("hardWordStatus"),
  masteredWordToggle: document.getElementById("masteredWordToggle"),
  masteredWordStatus: document.getElementById("masteredWordStatus"),
  statisticsSummary: document.getElementById("statisticsSummary"),
  statisticsSyncStatus: document.getElementById("statisticsSyncStatus"),
  statisticsList: document.getElementById("statisticsList"),
  frequentStatsButton: document.getElementById("frequentStatsButton"),
  forgottenStatsButton: document.getElementById("forgottenStatsButton"),
  syncStatsButton: document.getElementById("syncStatsButton"),
  settingsSummary: document.getElementById("settingsSummary"),
  settingsSyncStatus: document.getElementById("settingsSyncStatus"),
  syncSettingsButton: document.getElementById("syncSettingsButton"),
  exampleOneEn: document.getElementById("exampleOneEn"),
  exampleOneZh: document.getElementById("exampleOneZh"),
  exampleTwoEn: document.getElementById("exampleTwoEn"),
  exampleTwoZh: document.getElementById("exampleTwoZh"),
  playButton: document.getElementById("playButton"),
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
  elements.exampleOneEn.innerHTML = highlightExampleText(word.example_1_en, word.word, word.example_1_tense?.highlights);
  elements.exampleOneZh.innerHTML = renderTranslationWithTense(word.example_1_zh, word.example_1_tense);
  elements.exampleTwoEn.innerHTML = highlightExampleText(word.example_2_en, word.word, word.example_2_tense?.highlights);
  elements.exampleTwoZh.innerHTML = renderTranslationWithTense(word.example_2_zh, word.example_2_tense);
  elements.combinedAudioButton.textContent = `播放 ${chapter.title || "本章節"}`;

  document.body.classList.toggle("hidden-meaning", state.hideMeaning);
  renderChapterSelect();
  renderWordList();
  updateHardWordControls();
  updateMasteredControls();
  renderPracticeStatistics();
  updateSettingsControls();
  saveProgress();
}

function renderChapterSelect() {
  elements.chapterSelect.innerHTML = "";
  state.chapters.forEach((chapter, index) => {
    const option = document.createElement("option");
    option.value = chapterKey(chapter);
    option.textContent = `${chapter.title || `Chapter ${index + 1}`} (${chapterProgressText(chapter, index)})`;
    option.selected = index === state.currentChapterIndex;
    elements.chapterSelect.appendChild(option);
  });
}

function selectChapter(chapterId, synchronize = true) {
  const index = state.chapters.findIndex((chapter) => chapterKey(chapter) === chapterId);
  if (index < 0 || index === state.currentChapterIndex) {
    return;
  }
  stopQueue();
  saveCurrentChapterProgress();
  state.currentChapterIndex = index;
  state.currentIndex = Math.max(0, savedChapterIndex(state.chapters[index]));
  if (synchronize) {
    markPracticeSettingsChanged();
  }
  render();
  buildQuestion();
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

function playCurrent(isRepeatCycle = false) {
  const word = currentWord();
  const queue = buildWordQueue(word, isRepeatCycle);
  if (queue.length === 0 && word.audio) {
    playDirectAudio(word.audio, true, { word, isRepeatCycle });
    return;
  }
  playQueue(queue, false);
}

function resumeOrPlayCurrent() {
  if (state.isPaused && state.playbackQueue.length > 0) {
    state.pausedQueueIndex = Math.min(state.pausedQueueIndex, state.playbackQueue.length - 1);
    state.queueIndex = state.pausedQueueIndex;
    state.playbackQueue[state.queueIndex].delayMs = 0;
    state.isPaused = false;
    requestWakeLock();
    updateMediaSession();
    playNextQueueSegment();
    return;
  }
  playCurrent();
}

function togglePlayback() {
  if (elements.playButton.getAttribute("aria-pressed") === "true") {
    pausePlayback();
    return;
  }
  resumeOrPlayCurrent();
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
  const queue = [];
  currentWords().forEach((word) => {
    const wordQueue = buildWordQueue(word, false);
    if (queue.length > 0 && wordQueue.length > 0) {
      wordQueue[0].delayMs = WORD_GROUP_DELAY_MS;
    }
    queue.push(...wordQueue);
  });
  return queue;
}

function buildWordQueue(word, isRepeatCycle = false) {
  const segments = word?.audio_segments || {};
  const queue = [];
  const repeatCount = repeatCountForWord(
    isMasteredWord(word),
    state.englishRepeatCount,
    state.includeExamples,
  );
  addRepeatedEnglishWithChinese(queue, segments.word, word?.word, segments.meaning, word?.chinese_meaning, repeatCount);
  if (state.includeExamples) {
    addRepeatedEnglishWithChinese(queue, segments.example_1_en, word?.example_1_en, segments.example_1_zh, word?.example_1_zh, repeatCount);
    addRepeatedEnglishWithChinese(queue, segments.example_2_en, word?.example_2_en, segments.example_2_zh, word?.example_2_zh, repeatCount, EXAMPLE_GROUP_DELAY_MS);
  }
  if (queue.length > 0) {
    queue[queue.length - 1].completesWord = true;
    queue[queue.length - 1].practiceWord = word;
    queue[queue.length - 1].isRepeatCycle = isRepeatCycle;
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
  startDelayMs = 0,
) {
  const groupStartIndex = queue.length;
  addNarration(queue, englishSegment, "en");
  addNarration(queue, chineseSegment, "zh");
  for (let count = 1; count < repeatCount; count += 1) {
    addNarration(queue, englishSegment, "en", ENGLISH_REPEAT_DELAY_MS);
  }
  if (queue.length > groupStartIndex) {
    queue[groupStartIndex].delayMs = startDelayMs;
  }
}

function addNarration(queue, segment, fallbackLanguage, delayMs = 0) {
  if (segment?.src) {
    queue.push({
      src: segment.src,
      language: segment.language || fallbackLanguage,
      delayMs,
    });
  }
}

function playQueue(queue, isChapterPlayback) {
  if (queue.length === 0) {
    showPlaybackError("目前沒有可播放的音訊。");
    return;
  }
  stopQueue();
  state.playbackQueue = queue;
  state.queueIndex = 0;
  state.isPaused = false;
  state.pausedQueueIndex = 0;
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
    elements.audioPlayer.src = resolveAssetPath(segment.src);
    try {
      elements.audioPlayer.currentTime = 0;
    } catch (error) {
      // Some browsers reject seeking before metadata is available.
    }
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

function updateHardWordControls() {
  if (!elements.hardWordButton || !elements.hardWordStatus) {
    return;
  }
  if (!state.hardWordsWriteUrl) {
    elements.hardWordButton.hidden = true;
    elements.hardWordHelp.hidden = true;
    elements.hardWordStatus.textContent = "";
    return;
  }
  const word = currentWord();
  const wordKey = hardWordKey(word);
  const alreadyAdded = isHardWord(wordKey);
  const mastered = isMasteredWord(word);
  elements.hardWordButton.hidden = false;
  elements.hardWordButton.disabled = !word.word || mastered;
  elements.hardWordButton.textContent = alreadyAdded ? "從未熟記單字移除" : "加入未熟記單字";
  elements.hardWordHelp.hidden = !mastered;
  elements.hardWordStatus.textContent = alreadyAdded ? "目前在未熟記單字練習" : "";
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
  const repeatCount = repeatCountForWord(
    isMasteredWord(word),
    state.englishRepeatCount,
    state.includeExamples,
  );
  elements.masteredWordStatus.textContent = isMasteredWord(word)
    ? `英文播放 ${repeatCount} 次`
    : "";
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

function normalizePracticeStat(record, fallbackWord = "") {
  const word = String(record?.word || fallbackWord || "").trim();
  if (!word) {
    return null;
  }
  return {
    word,
    practice_count: Math.max(0, Number.parseInt(record?.practice_count, 10) || 0),
    repeat_current_count: Math.max(0, Number.parseInt(record?.repeat_current_count, 10) || 0),
    last_practiced_at: String(record?.last_practiced_at || ""),
  };
}

function mergePracticeStat(record) {
  const normalized = normalizePracticeStat(record);
  if (!normalized) {
    return;
  }
  const key = hardWordKey(normalized);
  const current = state.practiceStats.get(key);
  if (!current) {
    state.practiceStats.set(key, normalized);
    return;
  }
  state.practiceStats.set(key, {
    word: normalized.word || current.word,
    practice_count: Math.max(current.practice_count, normalized.practice_count),
    repeat_current_count: Math.max(current.repeat_current_count, normalized.repeat_current_count),
    last_practiced_at: normalized.last_practiced_at > current.last_practiced_at
      ? normalized.last_practiced_at
      : current.last_practiced_at,
  });
}

function readPracticeStatsLocalState() {
  const raw = localStorage.getItem(PRACTICE_STATS_LOCAL_KEY);
  if (!raw) {
    return { records: {}, settings: {}, settingsUpdatedAt: "", dirty: false, lastSyncAt: 0 };
  }
  try {
    const saved = JSON.parse(raw);
    return {
      records: saved?.records && typeof saved.records === "object" ? saved.records : {},
      settings: saved?.settings && typeof saved.settings === "object" ? saved.settings : {},
      settingsUpdatedAt: String(saved?.settingsUpdatedAt || ""),
      dirty: saved?.dirty === true,
      lastSyncAt: Number(saved?.lastSyncAt) || 0,
    };
  } catch (error) {
    localStorage.removeItem(PRACTICE_STATS_LOCAL_KEY);
    return { records: {}, settings: {}, settingsUpdatedAt: "", dirty: false, lastSyncAt: 0 };
  }
}

function restorePracticeState(cloudRecords = {}, cloudSettings = {}, cloudSettingsUpdatedAt = "") {
  state.practiceStats.clear();
  Object.entries(cloudRecords || {}).forEach(([wordKey, record]) => {
    mergePracticeStat(normalizePracticeStat(record, wordKey));
  });
  const local = readPracticeStatsLocalState();
  Object.entries(local.records).forEach(([wordKey, record]) => {
    mergePracticeStat(normalizePracticeStat(record, wordKey));
  });
  const cloudTimestamp = String(cloudSettingsUpdatedAt || "");
  const localTimestamp = String(local.settingsUpdatedAt || "");
  const hasCloudSettings = Object.keys(cloudSettings || {}).length > 0;
  const hasLocalSettings = Object.keys(local.settings || {}).length > 0;
  if (hasLocalSettings && (!hasCloudSettings || localTimestamp > cloudTimestamp)) {
    applyPracticeSettings(local.settings);
    state.practiceSettingsUpdatedAt = localTimestamp;
  } else if (hasCloudSettings) {
    applyPracticeSettings(cloudSettings);
    state.practiceSettingsUpdatedAt = cloudTimestamp;
  } else {
    state.practiceSettingsUpdatedAt = new Date().toISOString();
  }
  state.practiceStatsDirty = local.dirty;
  if (!hasCloudSettings && !hasLocalSettings) {
    state.practiceStatsDirty = true;
  }
  state.practiceStatsLastSyncAt = local.lastSyncAt;
  savePracticeStatistics();
  if (state.practiceStatsDirty) {
    schedulePracticeStatsSync();
  }
}

function currentPracticeSettings() {
  return {
    selected_chapter_id: chapterKey(currentChapter()),
    repeat_all: state.repeatAll,
    repeat_current: state.repeatCurrent,
    include_examples: state.includeExamples,
    playback_rate: state.playbackRate,
    english_repeat_count: state.englishRepeatCount,
  };
}

function applyPracticeSettings(settings) {
  if (typeof settings.repeat_all === "boolean") {
    state.repeatAll = settings.repeat_all;
  }
  if (typeof settings.repeat_current === "boolean") {
    state.repeatCurrent = settings.repeat_current;
  }
  if (typeof settings.include_examples === "boolean") {
    state.includeExamples = settings.include_examples;
  }
  const playbackRate = Number(settings.playback_rate);
  if (playbackRate >= 0.5 && playbackRate <= 1.5) {
    state.playbackRate = playbackRate;
  }
  state.englishRepeatCount = clampRepeatCount(
    settings.english_repeat_count ?? state.englishRepeatCount,
  );
  const chapterId = String(settings.selected_chapter_id || "");
  const chapterIndex = state.chapters.findIndex((chapter) => chapterKey(chapter) === chapterId);
  if (chapterIndex >= 0) {
    state.currentChapterIndex = chapterIndex;
    state.currentIndex = Math.max(0, savedChapterIndex(state.chapters[chapterIndex]));
  }
}

function markPracticeSettingsChanged() {
  state.practiceSettingsUpdatedAt = new Date().toISOString();
  state.practiceStatsDirty = true;
  savePracticeStatistics();
  updateSettingsControls();
  schedulePracticeStatsSync();
}

function practiceStatsObject() {
  return Object.fromEntries(
    [...state.practiceStats.entries()].map(([key, record]) => [key, { ...record }]),
  );
}

function savePracticeStatistics() {
  localStorage.setItem(PRACTICE_STATS_LOCAL_KEY, JSON.stringify({
    records: practiceStatsObject(),
    settings: currentPracticeSettings(),
    settingsUpdatedAt: state.practiceSettingsUpdatedAt,
    dirty: state.practiceStatsDirty,
    lastSyncAt: state.practiceStatsLastSyncAt,
  }));
}

function recordCompletedWordPractice(word, isRepeatCycle = false) {
  const key = hardWordKey(word);
  if (!key) {
    return;
  }
  const updated = incrementPracticeRecord(
    state.practiceStats.get(key),
    word.word,
    isRepeatCycle,
  );
  state.practiceStats.set(key, updated);
  state.practiceStatsDirty = true;
  savePracticeStatistics();
  renderPracticeStatistics();
  schedulePracticeStatsSync();
}

function currentWordPracticeStat() {
  return state.practiceStats.get(hardWordKey(currentWord())) || {
    practice_count: 0,
    repeat_current_count: 0,
  };
}

function renderPracticeStatistics() {
  if (!elements.statisticsList || !elements.currentWordStats) {
    return;
  }
  const current = currentWordPracticeStat();
  elements.currentWordStats.textContent = `練習 ${current.practice_count} 次 · 重複 ${current.repeat_current_count} 次`;

  const records = [...state.practiceStats.values()].filter((record) => record.practice_count > 0);
  const totalPractices = records.reduce((total, record) => total + record.practice_count, 0);
  elements.statisticsSummary.textContent = records.length > 0
    ? `(${records.length} 個單字 · ${totalPractices} 次練習)`
    : "(尚無練習紀錄)";
  const sorted = [...records].sort((first, second) => {
    if (state.practiceStatsView === "forgotten") {
      return second.repeat_current_count - first.repeat_current_count
        || second.practice_count - first.practice_count
        || first.word.localeCompare(second.word, "en");
    }
    return second.practice_count - first.practice_count
      || second.repeat_current_count - first.repeat_current_count
      || first.word.localeCompare(second.word, "en");
  });
  elements.statisticsList.innerHTML = sorted.length > 0
    ? sorted.map((record) => (
      `<div class="statistics-item">`
      + `<strong>${escapeHtml(record.word)}</strong>`
      + `<span>練習 ${record.practice_count}</span>`
      + `<span>重複 ${record.repeat_current_count}</span>`
      + `</div>`
    )).join("")
    : '<p class="sync-status">尚無練習紀錄</p>';
  const frequent = state.practiceStatsView === "frequent";
  elements.frequentStatsButton.classList.toggle("active", frequent);
  elements.forgottenStatsButton.classList.toggle("active", !frequent);
  elements.frequentStatsButton.setAttribute("aria-pressed", String(frequent));
  elements.forgottenStatsButton.setAttribute("aria-pressed", String(!frequent));
}

function setPracticeStatsView(view) {
  state.practiceStatsView = view;
  renderPracticeStatistics();
}

function updateSettingsControls() {
  elements.repeatAllToggle.checked = state.repeatAll;
  elements.repeatCurrentToggle.checked = state.repeatCurrent;
  elements.includeExamplesToggle.checked = state.includeExamples;
  elements.playbackRate.value = String(state.playbackRate);
  elements.playbackRateValue.textContent = `${state.playbackRate.toFixed(1)}x`;
  elements.exampleRepeatCount.value = String(state.englishRepeatCount);
  elements.exampleRepeatCountValue.textContent = String(state.englishRepeatCount);
  elements.settingsSummary.textContent = `(${state.playbackRate.toFixed(1)}x · 重複 ${state.englishRepeatCount} 次)`;
}

function compactPracticeStatsSnapshot() {
  const records = [...state.practiceStats.values()]
    .filter((record) => record.practice_count > 0)
    .sort((first, second) => first.word.localeCompare(second.word, "en"))
    .map((record) => [
      record.word,
      record.practice_count,
      record.repeat_current_count,
      record.last_practiced_at,
    ]);
  return JSON.stringify({
    v: 2,
    u: new Date().toISOString(),
    r: records,
    s: currentPracticeSettings(),
    su: state.practiceSettingsUpdatedAt,
  });
}

function practiceStatsPayload(passcode) {
  return {
    passcode,
    status: "practice_stats",
    added_at: new Date().toISOString(),
    source_chapter: "practice_statistics",
    source_id: "practice_statistics",
    id: "practice_statistics",
    word: PRACTICE_STATS_SENTINEL_WORD,
    pronunciation: "",
    chinese_meaning: "",
    example_1_en: "",
    example_1_zh: "",
    example_2_en: "",
    example_2_zh: "",
    category: "system",
    difficulty: "",
    review_count: "0",
    last_review_date: "",
    note: compactPracticeStatsSnapshot(),
  };
}

function schedulePracticeStatsSync() {
  if (!state.practiceStatsDirty || state.practiceStatsSyncTimer || !state.hardWordsWriteUrl) {
    return;
  }
  const sinceLastSync = Date.now() - state.practiceStatsLastSyncAt;
  const waitForThrottle = Math.max(0, PRACTICE_STATS_MIN_SYNC_INTERVAL_MS - sinceLastSync);
  const delay = Math.max(PRACTICE_STATS_SYNC_DELAY_MS, waitForThrottle);
  state.practiceStatsSyncTimer = window.setTimeout(() => {
    state.practiceStatsSyncTimer = null;
    syncPracticeStatistics(false);
  }, delay);
}

async function syncPracticeStatistics(promptForPasscode = true) {
  if (!state.hardWordsWriteUrl) {
    setCloudSyncStatus("尚未設定雲端同步");
    return;
  }
  const passcode = promptForPasscode
    ? getHardWordsPasscode()
    : localStorage.getItem(HARD_WORDS_PASSCODE_KEY) || "";
  if (!passcode) {
    setCloudSyncStatus("點選同步按鈕以設定同步密碼");
    return;
  }
  if (state.practiceStatsSyncTimer) {
    window.clearTimeout(state.practiceStatsSyncTimer);
    state.practiceStatsSyncTimer = null;
  }
  elements.syncStatsButton.disabled = true;
  elements.syncSettingsButton.disabled = true;
  setCloudSyncStatus("同步中...");
  try {
    const response = await fetch(state.hardWordsWriteUrl, {
      method: "POST",
      mode: "no-cors",
      headers: { "Content-Type": "text/plain;charset=utf-8" },
      body: JSON.stringify(practiceStatsPayload(passcode)),
    });
    if (response.type !== "opaque" && !response.ok) {
      throw new Error("Practice statistics sync failed.");
    }
    state.practiceStatsDirty = false;
    state.practiceStatsLastSyncAt = Date.now();
    savePracticeStatistics();
    setCloudSyncStatus("已送出同步");
  } catch (error) {
    state.practiceStatsDirty = true;
    savePracticeStatistics();
    setCloudSyncStatus("同步失敗，將稍後重試");
    schedulePracticeStatsSync();
  } finally {
    elements.syncStatsButton.disabled = false;
    elements.syncSettingsButton.disabled = false;
  }
}

function setCloudSyncStatus(message) {
  elements.statisticsSyncStatus.textContent = message;
  elements.settingsSyncStatus.textContent = message;
}

function sendPracticeStatisticsOnPageHide() {
  const passcode = localStorage.getItem(HARD_WORDS_PASSCODE_KEY) || "";
  if (!state.practiceStatsDirty || !state.hardWordsWriteUrl || !passcode || !navigator.sendBeacon) {
    return;
  }
  const body = new Blob(
    [JSON.stringify(practiceStatsPayload(passcode))],
    { type: "text/plain;charset=utf-8" },
  );
  navigator.sendBeacon(state.hardWordsWriteUrl, body);
}

function handleAudioEnded() {
  const segment = currentQueueSegment();
  if (segment.completesWord) {
    recordCompletedWordPractice(segment.practiceWord, segment.isRepeatCycle);
  } else if (state.directPlayback?.word) {
    recordCompletedWordPractice(
      state.directPlayback.word,
      state.directPlayback.isRepeatCycle,
    );
    state.directPlayback = null;
  }
  playNextQueueSegment();
}

function finishQueue() {
  if (state.isChapterPlayback) {
    state.isChapterPlayback = false;
    releaseWakeLock();
    updateMediaSessionPlaybackState("none");
    return;
  }
  if (state.repeatCurrent) {
    scheduleCurrentWordRepeat();
    return;
  }
  scheduleNextWord();
}

function scheduleCurrentWordRepeat() {
  state.playbackQueue = [];
  state.queueIndex = 0;
  state.isPaused = false;
  state.pausedQueueIndex = 0;
  state.queueTimer = window.setTimeout(() => {
    state.queueTimer = null;
    playCurrent(true);
  }, REPEAT_CURRENT_DELAY_MS);
}

function scheduleNextWord() {
  state.playbackQueue = [];
  state.queueIndex = 0;
  state.isPaused = false;
  state.pausedQueueIndex = 0;
  state.queueTimer = window.setTimeout(() => {
    state.queueTimer = null;
    const autoplay = state.repeatAll;
    nextWord(autoplay);
    if (!autoplay) {
      releaseWakeLock();
      updateMediaSessionPlaybackState("none");
    }
  }, WORD_GROUP_DELAY_MS);
}

function stopQueue() {
  if (state.queueTimer) {
    window.clearTimeout(state.queueTimer);
    state.queueTimer = null;
  }
  state.playbackQueue = [];
  state.queueIndex = 0;
  state.isPaused = false;
  state.pausedQueueIndex = 0;
  state.isChapterPlayback = false;
  state.directPlayback = null;
  state.wantsWakeLock = false;
  releaseWakeLock();
  updateMediaSessionPlaybackState("none");
  elements.audioPlayer.pause();
}

function playDirectAudio(src, language, tracking = null) {
  stopQueue();
  state.directPlayback = tracking;
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
    resumeOrPlayCurrent();
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
  setPlaybackStatus("playing");
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
  setPlaybackStatus(playbackState);
  if ("mediaSession" in navigator) {
    navigator.mediaSession.playbackState = playbackState;
  }
}

function setPlaybackStatus(playbackState) {
  const isPlaying = playbackState === "playing";
  elements.playButton.classList.toggle("active", isPlaying);
  elements.playButton.setAttribute("aria-pressed", String(isPlaying));
  elements.playButton.textContent = isPlaying ? "暫停" : "播放";
}

function pausePlayback() {
  if (state.queueTimer) {
    window.clearTimeout(state.queueTimer);
    state.queueTimer = null;
  }
  if (state.playbackQueue.length > 0) {
    state.isPaused = true;
    state.pausedQueueIndex = Math.max(0, state.queueIndex - 1);
  }
  elements.audioPlayer.pause();
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
    source: findVocabularySource(candidate.word, state.chapters),
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
  const sourceText = current.source
    ? `（出處：${current.source.chapterTitle}，第 ${current.source.wordIndex} 個單字）`
    : "";
  if (isCorrectClozeAnswer(answer, current.correctAnswer)) {
    state.practice.correct += 1;
    elements.answerFeedback.textContent = `答對${sourceText}`;
    elements.answerFeedback.className = "feedback correct";
  } else {
    const formalWords = state.chapters
      .filter((chapter) => !chapter.is_hard_words)
      .flatMap((chapter) => chapter.words || []);
    const closest = findClosestVocabularyMatch(answer, formalWords);
    const pluralExplanation = describePluralAnswerRequirement(answer, current.correctAnswer);
    renderWrongAnswerFeedback(answer, current.correctAnswer, sourceText, closest, pluralExplanation);
    elements.answerFeedback.className = "feedback wrong";
  }
  elements.clozeAnswerInput.disabled = true;
  elements.submitAnswerButton.disabled = true;
  updatePracticeScore();
  saveProgress();
}

function renderWrongAnswerFeedback(input, correctAnswer, sourceText, closest, pluralExplanation) {
  elements.answerFeedback.textContent = "";
  elements.answerFeedback.append(document.createTextNode("答錯，答案是 "));
  buildSuggestionSegments(input, correctAnswer).forEach((segment) => {
    if (!segment.changed) {
      elements.answerFeedback.append(document.createTextNode(segment.text));
      return;
    }
    const difference = document.createElement("strong");
    difference.className = "suggestion-difference";
    difference.textContent = segment.text;
    elements.answerFeedback.append(difference);
  });
  elements.answerFeedback.append(document.createTextNode(sourceText));
  if (pluralExplanation) {
    const explanationLine = document.createElement("span");
    explanationLine.className = "plural-explanation";
    explanationLine.textContent = pluralExplanation;
    elements.answerFeedback.append(explanationLine);
    return;
  }
  if (!closest) {
    return;
  }
  const suggestionLine = document.createElement("span");
  suggestionLine.className = "suggestion-line";
  suggestionLine.textContent = `你輸入的 ${String(input).trim()} 可能是 ${closest.word.word}：${closest.word.chinese_meaning || "無中文意思"}`;
  elements.answerFeedback.append(suggestionLine);
}

function submitCurrentAnswer() {
  answerQuestion(elements.clozeAnswerInput.value);
}

function updatePracticeScore() {
  elements.practiceScore.textContent = `(正確率${state.practice.correct}/${state.practice.attempts})`;
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

function highlightExampleText(text, target, tenseHighlights = []) {
  const value = String(text || "");
  const keyword = String(target || "").trim();
  if (!value) {
    return "";
  }
  const ranges = [];
  if (keyword) {
    findTargetPhraseMatches(value, keyword).forEach((match) => {
      ranges.push({ start: match.start, end: match.end, className: "example-target" });
    });
  }
  findLiteralHighlightRanges(value, tenseHighlights).forEach((range) => {
    ranges.push({ ...range, className: "tense-target" });
  });
  if (ranges.length === 0) {
    return escapeHtml(value);
  }
  return renderHighlightedRanges(value, ranges);
}

function renderHighlightedRanges(value, ranges) {
  const boundaries = Array.from(new Set([
    0,
    value.length,
    ...ranges.flatMap((range) => [range.start, range.end]),
  ])).filter((index) => index >= 0 && index <= value.length).sort((first, second) => first - second);
  let html = "";
  for (let index = 0; index < boundaries.length - 1; index += 1) {
    const start = boundaries[index];
    const end = boundaries[index + 1];
    const text = value.slice(start, end);
    if (!text) {
      continue;
    }
    const classNames = Array.from(new Set(
      ranges
        .filter((range) => start >= range.start && end <= range.end)
        .map((range) => range.className),
    ));
    const escaped = escapeHtml(text);
    html += classNames.length > 0
      ? `<span class="${classNames.join(" ")}">${escaped}</span>`
      : escaped;
  }
  return html;
}

function renderTranslationWithTense(translation, tense) {
  const text = escapeHtml(translation || "");
  const translationHtml = `<span class="translation-text">${text}</span>`;
  const name = String(tense?.display_name_zh || tense?.name_zh || "").trim();
  const formula = String(tense?.display_formula || tense?.formula || "").trim();
  if (!name || !formula) {
    return translationHtml;
  }
  return `${translationHtml}<br><span class="tense-note">(${escapeHtml(name)}&#65306;${escapeHtml(formula)})</span>`;
}

elements.playButton.addEventListener("click", togglePlayback);
elements.nextButton.addEventListener("click", () => {
  stopQueue();
  nextWord(true);
});
elements.previousButton.addEventListener("click", () => {
  stopQueue();
  previousWord();
  playCurrent();
});
elements.combinedAudioButton.addEventListener("click", playCombinedAudio);
elements.chapterSelect.addEventListener("change", (event) => {
  selectChapter(event.target.value, true);
});
elements.repeatAllToggle.addEventListener("change", (event) => {
  state.repeatAll = event.target.checked;
  markPracticeSettingsChanged();
});
elements.repeatCurrentToggle.addEventListener("change", (event) => {
  state.repeatCurrent = event.target.checked;
  markPracticeSettingsChanged();
});
elements.includeExamplesToggle.addEventListener("change", (event) => {
  state.includeExamples = event.target.checked;
  updateMasteredControls();
  markPracticeSettingsChanged();
});
elements.playbackRate.addEventListener("input", (event) => {
  state.playbackRate = Number(event.target.value);
  applyPlaybackRate();
  markPracticeSettingsChanged();
});
elements.exampleRepeatCount.addEventListener("input", (event) => {
  state.englishRepeatCount = clampRepeatCount(event.target.value);
  applyPlaybackRate();
  updateMasteredControls();
  markPracticeSettingsChanged();
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
elements.frequentStatsButton.addEventListener("click", () => setPracticeStatsView("frequent"));
elements.forgottenStatsButton.addEventListener("click", () => setPracticeStatsView("forgotten"));
elements.syncStatsButton.addEventListener("click", () => syncPracticeStatistics(true));
elements.syncSettingsButton.addEventListener("click", () => syncPracticeStatistics(true));
elements.audioPlayer.addEventListener("ended", handleAudioEnded);
elements.audioPlayer.addEventListener("loadedmetadata", () => applyPlaybackRate());
elements.audioPlayer.addEventListener("play", () => applyPlaybackRate());
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && state.wantsWakeLock) {
    requestWakeLock();
  } else if (document.visibilityState === "hidden") {
    sendPracticeStatisticsOnPageHide();
  }
});
window.addEventListener("pagehide", sendPracticeStatisticsOnPageHide);

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
    restorePracticeState(
      data.practice_stats?.records || {},
      data.practice_stats?.settings || {},
      data.practice_stats?.settings_updated_at || "",
    );
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
