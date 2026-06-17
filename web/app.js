const DEFAULT_PLAYBACK_RATE = 0.8;

const state = {
  data: null,
  currentIndex: 0,
  hideMeaning: false,
  repeatAll: true,
  repeatCurrent: false,
  playbackRate: DEFAULT_PLAYBACK_RATE,
  practice: {
    current: null,
    attempts: 0,
    correct: 0,
  },
};

const elements = {
  courseDate: document.getElementById("courseDate"),
  progressText: document.getElementById("progressText"),
  wordList: document.getElementById("wordList"),
  categoryText: document.getElementById("categoryText"),
  wordText: document.getElementById("wordText"),
  pronunciationText: document.getElementById("pronunciationText"),
  meaningText: document.getElementById("meaningText"),
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
  playbackRate: document.getElementById("playbackRate"),
  playbackRateValue: document.getElementById("playbackRateValue"),
  combinedAudioButton: document.getElementById("combinedAudioButton"),
  toggleMeaningButton: document.getElementById("toggleMeaningButton"),
  audioPlayer: document.getElementById("audioPlayer"),
  practiceScore: document.getElementById("practiceScore"),
  questionMode: document.getElementById("questionMode"),
  questionText: document.getElementById("questionText"),
  answerOptions: document.getElementById("answerOptions"),
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

function render() {
  const words = state.data.words;
  const word = words[state.currentIndex];
  elements.courseDate.textContent = state.data.date;
  elements.progressText.textContent = `${state.currentIndex + 1} / ${words.length}`;
  elements.categoryText.textContent = `${word.category || "Category"} · Difficulty ${word.difficulty || "-"}`;
  elements.wordText.textContent = word.word;
  elements.pronunciationText.textContent = word.pronunciation;
  elements.meaningText.textContent = word.chinese_meaning;
  elements.exampleOneEn.textContent = word.example_1_en;
  elements.exampleOneZh.textContent = word.example_1_zh;
  elements.exampleTwoEn.textContent = word.example_2_en;
  elements.exampleTwoZh.textContent = word.example_2_zh;

  document.body.classList.toggle("hidden-meaning", state.hideMeaning);
  renderWordList();
  saveProgress();
}

function renderWordList() {
  elements.wordList.innerHTML = "";
  state.data.words.forEach((word, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `word-item${index === state.currentIndex ? " active" : ""}`;
    button.innerHTML = `<strong>${index + 1}. ${escapeHtml(word.word)}</strong><small>${escapeHtml(word.chinese_meaning)}</small>`;
    button.addEventListener("click", () => {
      state.currentIndex = index;
      render();
      playCurrent();
    });
    elements.wordList.appendChild(button);
  });
}

function playCurrent() {
  const word = state.data.words[state.currentIndex];
  if (!word.audio) {
    elements.answerFeedback.textContent = "這個單字沒有音訊檔。";
    elements.answerFeedback.className = "feedback wrong";
    return;
  }
  elements.audioPlayer.src = resolveAssetPath(word.audio);
  applyPlaybackRate();
  elements.audioPlayer.play().catch(() => {
    elements.answerFeedback.textContent = "請先按一次開始播放。";
    elements.answerFeedback.className = "feedback wrong";
  });
}

function playCombinedAudio() {
  if (!state.data.combined_audio) {
    return;
  }
  elements.audioPlayer.src = resolveAssetPath(state.data.combined_audio);
  applyPlaybackRate();
  elements.audioPlayer.play().catch(() => {
    elements.answerFeedback.textContent = "請先按一次播放按鈕。";
    elements.answerFeedback.className = "feedback wrong";
  });
}

function nextWord(autoplay = false) {
  const lastIndex = state.data.words.length - 1;
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
  const lastIndex = state.data.words.length - 1;
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
  const words = state.data.words;
  const word = words[Math.floor(Math.random() * words.length)];
  const askEnglish = Math.random() >= 0.5;
  const correctAnswer = askEnglish ? word.chinese_meaning : word.word;
  const options = shuffle([
    correctAnswer,
    ...shuffle(words.filter((item) => item.id !== word.id))
      .slice(0, 3)
      .map((item) => (askEnglish ? item.chinese_meaning : item.word)),
  ]);

  state.practice.current = { word, correctAnswer };
  elements.questionMode.textContent = askEnglish ? "English → Chinese" : "Chinese → English";
  elements.questionText.textContent = askEnglish ? word.word : word.chinese_meaning;
  elements.answerFeedback.textContent = "";
  elements.answerFeedback.className = "feedback";
  elements.answerOptions.innerHTML = "";

  options.forEach((option) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = option;
    button.addEventListener("click", () => answerQuestion(option));
    elements.answerOptions.appendChild(button);
  });
}

function answerQuestion(answer) {
  const current = state.practice.current;
  if (!current) {
    return;
  }
  state.practice.attempts += 1;
  if (answer === current.correctAnswer) {
    state.practice.correct += 1;
    elements.answerFeedback.textContent = "答對";
    elements.answerFeedback.className = "feedback correct";
  } else {
    elements.answerFeedback.textContent = `答案：${current.correctAnswer}`;
    elements.answerFeedback.className = "feedback wrong";
  }
  updatePracticeScore();
  saveProgress();
}

function updatePracticeScore() {
  elements.practiceScore.textContent = `${state.practice.correct} / ${state.practice.attempts}`;
}

function applyPlaybackRate() {
  elements.audioPlayer.playbackRate = state.playbackRate;
  elements.playbackRate.value = String(state.playbackRate);
  elements.playbackRateValue.textContent = `${state.playbackRate.toFixed(1)}x`;
}

function saveProgress() {
  if (!state.data) {
    return;
  }
  const key = `evd-progress-${state.data.date}`;
  localStorage.setItem(
    key,
    JSON.stringify({
      currentIndex: state.currentIndex,
      playbackRate: state.playbackRate,
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
    state.currentIndex = Math.min(saved.currentIndex || 0, state.data.words.length - 1);
    state.playbackRate = Number(saved.playbackRate || DEFAULT_PLAYBACK_RATE);
    state.practice.attempts = saved.practice?.attempts || 0;
    state.practice.correct = saved.practice?.correct || 0;
  } catch (error) {
    localStorage.removeItem(key);
  }
}

function shuffle(items) {
  return [...items].sort(() => Math.random() - 0.5);
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
elements.pauseButton.addEventListener("click", () => elements.audioPlayer.pause());
elements.nextButton.addEventListener("click", () => nextWord(false));
elements.previousButton.addEventListener("click", previousWord);
elements.combinedAudioButton.addEventListener("click", playCombinedAudio);
elements.repeatAllToggle.addEventListener("change", (event) => {
  state.repeatAll = event.target.checked;
});
elements.repeatCurrentToggle.addEventListener("change", (event) => {
  state.repeatCurrent = event.target.checked;
});
elements.playbackRate.addEventListener("input", (event) => {
  state.playbackRate = Number(event.target.value);
  applyPlaybackRate();
  saveProgress();
});
elements.toggleMeaningButton.addEventListener("click", () => {
  state.hideMeaning = !state.hideMeaning;
  elements.toggleMeaningButton.textContent = state.hideMeaning ? "顯示中文" : "隱藏中文";
  render();
});
elements.nextQuestionButton.addEventListener("click", buildQuestion);
elements.audioPlayer.addEventListener("ended", () => {
  if (state.repeatCurrent) {
    playCurrent();
    return;
  }
  nextWord(true);
});
elements.audioPlayer.addEventListener("loadedmetadata", applyPlaybackRate);
elements.audioPlayer.addEventListener("play", applyPlaybackRate);

loadDailyData()
  .then((data) => {
    state.data = data;
    restoreProgress();
    applyPlaybackRate();
    render();
    buildQuestion();
    updatePracticeScore();
  })
  .catch((error) => {
    elements.wordText.textContent = "找不到每日單字資料";
    elements.meaningText.textContent = error.message;
  });
