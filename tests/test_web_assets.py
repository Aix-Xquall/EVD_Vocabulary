from pathlib import Path
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]


class WebAssetsTests(unittest.TestCase):
    def test_web_player_exposes_default_08x_playback_rate_control(self):
        index_html = (PROJECT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="playbackRate"', index_html)
        self.assertIn('value="0.8"', index_html)
        self.assertIn("DEFAULT_PLAYBACK_RATE = 0.8", app_js)
        self.assertIn("audioPlayer.playbackRate", app_js)
        self.assertIn('audioPlayer.addEventListener("loadedmetadata"', app_js)

    def test_web_player_exposes_chapters_and_english_repeat_controls(self):
        index_html = (PROJECT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="chapterTabs"', index_html)
        self.assertNotIn('id="courseDate"', index_html)
        self.assertNotIn('id="progressText"', index_html)
        self.assertNotIn("courseDate", app_js)
        self.assertNotIn("progressText", app_js)
        self.assertIn('id="includeExamplesToggle"', index_html)
        self.assertIn('id="exampleRepeatCount"', index_html)
        self.assertIn('min="1"', index_html)
        self.assertIn('max="5"', index_html)
        self.assertIn('value="3"', index_html)
        self.assertIn("DEFAULT_ENGLISH_REPEAT_COUNT = 3", app_js)
        self.assertIn("includeExamples: true", app_js)
        self.assertIn("includeExamplesToggle", app_js)
        self.assertIn("buildWordQueue", app_js)
        self.assertIn("buildChapterQueue", app_js)
        self.assertIn("addRepeatedEnglishWithChinese", app_js)
        self.assertIn("if (state.includeExamples)", app_js)
        self.assertIn('segment.language === "en" ? state.playbackRate : 1', app_js)
        self.assertNotIn("speechSynthesis", app_js)
        self.assertNotIn("SpeechSynthesisUtterance", app_js)

    def test_hard_words_chapter_is_first_and_tabs_show_progress(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function sortHardWordsFirst(chapters)", app_js)
        self.assertIn("Number(Boolean(second.is_hard_words))", app_js)
        self.assertIn("function chapterProgressText(chapter, index)", app_js)
        self.assertIn("saveCurrentChapterProgress()", app_js)
        self.assertIn("chapterProgress: state.chapterProgress", app_js)
        self.assertIn("state.chapters.unshift(chapter)", app_js)
        self.assertIn("`${chapter.title || `Chapter ${index + 1}`} (${chapterProgressText(chapter, index)})`", app_js)

    def test_word_and_examples_share_the_same_repeat_behavior(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn(
            'addRepeatedEnglishWithChinese(queue, segments.word, word?.word, segments.meaning, word?.chinese_meaning, repeatCount)',
            app_js,
        )
        self.assertIn("for (let count = 1; count < repeatCount; count += 1)", app_js)
        self.assertNotIn("addNarration(queue, segments.word, word?.word, \"en\");", app_js)

    def test_word_list_scrolls_when_chapter_has_many_words(self):
        styles_css = (PROJECT_DIR / "web" / "styles.css").read_text(encoding="utf-8")

        self.assertIn(".word-items", styles_css)
        self.assertIn("max-height: calc(100vh - 260px)", styles_css)
        self.assertIn("overflow-y: auto", styles_css)

    def test_mobile_layout_places_player_before_word_list(self):
        styles_css = (PROJECT_DIR / "web" / "styles.css").read_text(encoding="utf-8")

        self.assertIn("@media (max-width: 820px)", styles_css)
        self.assertIn(".study-panel {\n    order: 1;", styles_css)
        self.assertIn(".word-list {\n    order: 2;", styles_css)
        self.assertIn(".word-items {\n    max-height: 70vh;", styles_css)
        self.assertIn(".word-item strong {\n    font-size: 1.25rem;", styles_css)

    def test_active_word_is_centered_inside_scrollable_word_list(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("scrollActiveWordIntoView", app_js)
        self.assertIn("container.getBoundingClientRect()", app_js)
        self.assertIn("activeButton.getBoundingClientRect()", app_js)
        self.assertIn("container.scrollTop + activeRect.top - containerRect.top", app_js)
        self.assertIn("Math.max(0, targetTop)", app_js)
        self.assertIn("container.scrollTop =", app_js)
        self.assertNotIn("activeButton.offsetTop - container.clientHeight / 2", app_js)

    def test_web_player_uses_only_generated_cloud_tts_segments(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("if (segment?.src)", app_js)
        self.assertNotIn("fallbackText", app_js)
        self.assertNotIn("speakTextSegment", app_js)
        self.assertNotIn("speechTextForAudio", app_js)
        self.assertNotIn("expandKnownAbbreviationsForSpeech", app_js)

    def test_web_player_exposes_hard_words_sync_controls(self):
        index_html = (PROJECT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="hardWordButton"', index_html)
        self.assertIn('id="hardWordStatus"', index_html)
        self.assertIn("hardWordsWriteUrl", app_js)
        self.assertIn("toggleHardWord", app_js)
        self.assertIn("localStorage.getItem(HARD_WORDS_PASSCODE_KEY)", app_js)
        self.assertIn('fetch(state.hardWordsWriteUrl', app_js)
        self.assertIn('active: "active"', app_js)
        self.assertIn('removed: "removed"', app_js)
        self.assertIn("加入未熟記單字練習", app_js)
        self.assertIn("從未熟記單字移除", app_js)
        self.assertIn('"status": status', app_js)

    def test_web_player_exposes_mastered_word_controls_and_two_repeat_behavior(self):
        index_html = (PROJECT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")
        styles_css = (PROJECT_DIR / "web" / "styles.css").read_text(encoding="utf-8")

        self.assertIn('id="masteredWordToggle"', index_html)
        self.assertNotIn('id="skipMasteredToggle"', index_html)
        self.assertIn("mastered_active", app_js)
        self.assertIn("function isMasteredWord(word)", app_js)
        self.assertIn("function toggleMasteredWord", app_js)
        self.assertNotIn("skipMastered", app_js)
        self.assertIn(
            "repeatCountForWord(\n"
            "    isMasteredWord(word),\n"
            "    state.englishRepeatCount,\n"
            "    state.includeExamples,\n"
            "  )",
            app_js,
        )
        self.assertIn("`英文播放 ${repeatCount} 次`", app_js)
        self.assertIn("MASTERED_WORDS_LOCAL_KEY", app_js)
        self.assertIn("word-item mastered", app_js)
        self.assertIn(".word-item.mastered", styles_css)

    def test_daily_practice_uses_example_cloze_text_input(self):
        index_html = (PROJECT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="questionHint"', index_html)
        self.assertIn('id="clozeAnswerInput"', index_html)
        self.assertIn('id="submitAnswerButton"', index_html)
        self.assertNotIn('id="answerOptions"', index_html)
        self.assertIn("buildClozeCandidates(currentWords())", app_js)
        self.assertIn("isCorrectClozeAnswer(answer, current.correctAnswer)", app_js)
        self.assertIn('"本章節沒有可用的填空例句"', app_js)

    def test_pronunciation_display_omits_external_url(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")
        index_html = (PROJECT_DIR / "web" / "index.html").read_text(encoding="utf-8")

        self.assertIn("sanitizePronunciation(word.pronunciation)", app_js)
        self.assertIn('<script src="learning_helpers.js"></script>', index_html)

    def test_current_word_title_uses_smaller_type(self):
        styles_css = (PROJECT_DIR / "web" / "styles.css").read_text(encoding="utf-8")

        self.assertIn("font-size: clamp(1.6rem, 4vw, 3rem)", styles_css)
        self.assertIn(".current-word h2 {\n    font-size: 2.25rem;", styles_css)
        self.assertIn("overflow-wrap: anywhere", styles_css)
        self.assertNotIn("font-size: clamp(2rem, 6vw, 4rem)", styles_css)

    def test_english_examples_highlight_target_word(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")
        styles_css = (PROJECT_DIR / "web" / "styles.css").read_text(encoding="utf-8")

        self.assertIn("highlightExampleText(word.example_1_en, word.word, word.example_1_tense?.highlights)", app_js)
        self.assertIn("highlightExampleText(word.example_2_en, word.word, word.example_2_tense?.highlights)", app_js)
        self.assertIn("function highlightExampleText(text, target, tenseHighlights = [])", app_js)
        self.assertIn("findTargetPhraseMatches(value, keyword)", app_js)
        self.assertIn("word.example_1_tense?.highlights", app_js)
        self.assertIn("renderTranslationWithTense(word.example_1_zh, word.example_1_tense)", app_js)
        self.assertIn("function renderTranslationWithTense(translation, tense)", app_js)
        self.assertIn("tense?.display_name_zh || tense?.name_zh", app_js)
        self.assertIn("tense?.display_formula || tense?.formula", app_js)
        self.assertNotIn("modalNote", app_js)
        self.assertIn("tense-target", app_js)
        self.assertIn("tense-note", app_js)
        self.assertIn(".tense-target", styles_css)
        self.assertIn(".tense-note", styles_css)
        self.assertIn('className: "example-target"', app_js)
        self.assertIn(".example-target", styles_css)
        self.assertIn("color: var(--blue)", styles_css)
        self.assertIn("font-weight: 700", styles_css)

    def test_pause_then_play_restarts_current_queue_segment(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("isPaused: false", app_js)
        self.assertIn("pausedQueueIndex: 0", app_js)
        self.assertIn("function resumeOrPlayCurrent()", app_js)
        self.assertIn("state.queueIndex = state.pausedQueueIndex;", app_js)
        self.assertIn("state.pausedQueueIndex = Math.max(0, state.queueIndex - 1);", app_js)
        self.assertIn("elements.audioPlayer.currentTime = 0;", app_js)
        self.assertIn('elements.playButton.addEventListener("click", resumeOrPlayCurrent);', app_js)

    def test_hard_words_chapter_count_updates_immediately_after_toggle(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("chapterWordCount(chapter)", app_js)
        self.assertIn("function hardWordsChapter()", app_js)
        self.assertIn("function applyHardWordLocalState(word, status)", app_js)
        self.assertIn("applyHardWordLocalState(word, nextStatus)", app_js)
        self.assertIn("chapter.words.unshift({ ...word })", app_js)
        self.assertIn("chapter.words.splice(existingIndex, 1)", app_js)
        self.assertIn("chapter.word_count = chapter.words.length", app_js)

    def test_hard_words_local_state_survives_page_reload(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn('const HARD_WORDS_LOCAL_KEY = "evd-hard-words-local-state"', app_js)
        self.assertIn("function restoreHardWordsLocalState()", app_js)
        self.assertIn("function saveHardWordsLocalState(word, status)", app_js)
        self.assertIn("restoreHardWordsLocalState();", app_js)
        self.assertIn("saveHardWordsLocalState(word, nextStatus);", app_js)
        self.assertIn("localStorage.getItem(HARD_WORDS_LOCAL_KEY)", app_js)
        self.assertIn("localStorage.setItem(HARD_WORDS_LOCAL_KEY", app_js)
        self.assertIn("saved.active.unshift({ ...word })", app_js)
        self.assertIn("saved.active.slice().reverse().forEach(", app_js)
        self.assertIn("saved.removed.forEach((wordKey) => applyHardWordLocalState({ word: wordKey }, HARD_WORD_STATUS.removed))", app_js)

    def test_player_uses_wake_lock_and_media_session_for_mobile_playback(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("requestWakeLock", app_js)
        self.assertIn('navigator.wakeLock.request("screen")', app_js)
        self.assertIn("releaseWakeLock", app_js)
        self.assertIn('document.addEventListener("visibilitychange"', app_js)
        self.assertIn("setupMediaSession", app_js)
        self.assertIn("navigator.mediaSession.metadata", app_js)
        self.assertIn("new MediaMetadata", app_js)
        self.assertIn('navigator.mediaSession.setActionHandler("play"', app_js)
        self.assertIn('navigator.mediaSession.setActionHandler("pause"', app_js)
        self.assertIn('navigator.mediaSession.setActionHandler("nexttrack"', app_js)
        self.assertIn('navigator.mediaSession.setActionHandler("previoustrack"', app_js)

    def test_practice_statistics_are_counted_and_synced_across_devices(self):
        index_html = (PROJECT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn('class="statistics-panel"', index_html)
        self.assertIn('id="currentWordStats"', index_html)
        self.assertIn('id="syncStatsButton"', index_html)
        self.assertIn("function recordCompletedWordPractice", app_js)
        self.assertIn("segment.completesWord", app_js)
        self.assertIn("incrementPracticeRecord", app_js)
        self.assertIn("playCurrent(true)", app_js)
        self.assertIn("PRACTICE_STATS_SENTINEL_WORD", app_js)
        self.assertIn("compactPracticeStatsSnapshot", app_js)
        self.assertIn("PRACTICE_STATS_SYNC_DELAY_MS = 60000", app_js)
        self.assertIn("navigator.sendBeacon", app_js)
        self.assertIn("restorePracticeStatistics(data.practice_stats?.records || {})", app_js)

    def test_chapter_playback_uses_segment_queue_with_wake_lock_controls(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("const chapterQueue = buildChapterQueue()", app_js)
        self.assertIn("playQueue(chapterQueue, true)", app_js)
        self.assertNotIn("chapter.chapter_audio", app_js)
        self.assertNotIn('playDirectAudio(chapter.chapter_audio, "mixed")', app_js)

    def test_chapter_playback_waits_two_seconds_between_words(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("const WORD_GROUP_DELAY_MS = 2000;", app_js)
        self.assertIn("wordQueue[0].delayMs = WORD_GROUP_DELAY_MS;", app_js)
        self.assertIn("queue.push(...wordQueue);", app_js)

    def test_single_word_autoplay_waits_before_switching_to_next_word(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function scheduleNextWord()", app_js)
        self.assertIn("window.setTimeout(() => {", app_js)
        self.assertIn("nextWord(autoplay);", app_js)
        self.assertIn("}, WORD_GROUP_DELAY_MS);", app_js)
        self.assertIn("function nextWord(autoplay = false)", app_js)
        self.assertNotIn("nextWord(state.repeatAll, WORD_GROUP_DELAY_MS);", app_js)

    def test_repeat_current_waits_one_and_a_half_seconds_before_restarting(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("const REPEAT_CURRENT_DELAY_MS = 1500;", app_js)
        self.assertIn("function scheduleCurrentWordRepeat()", app_js)
        self.assertIn("scheduleCurrentWordRepeat();", app_js)
        self.assertIn("}, REPEAT_CURRENT_DELAY_MS);", app_js)

    def test_play_and_pause_buttons_reflect_the_current_playback_state(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")
        index_html = (PROJECT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        styles_css = (PROJECT_DIR / "web" / "styles.css").read_text(encoding="utf-8")

        self.assertIn("function setPlaybackStatus(playbackState)", app_js)
        self.assertIn('setPlaybackStatus("playing");', app_js)
        self.assertIn("setPlaybackStatus(playbackState);", app_js)
        self.assertIn('elements.playButton.setAttribute("aria-pressed", String(isPlaying));', app_js)
        self.assertIn('elements.pauseButton.setAttribute("aria-pressed", String(isPaused));', app_js)
        self.assertIn('id="playButton" class="playback-button"', index_html)
        self.assertIn('id="pauseButton" class="playback-button"', index_html)
        self.assertIn(".playback-button.active", styles_css)

    def test_previous_and_next_buttons_start_cloud_audio(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("elements.nextButton.addEventListener", app_js)
        self.assertIn("nextWord(true);", app_js)
        self.assertIn("elements.previousButton.addEventListener", app_js)
        self.assertIn("previousWord();\n  playCurrent();", app_js)

    def test_example_two_starts_after_two_second_group_delay(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("const ENGLISH_REPEAT_DELAY_MS = 1500;", app_js)
        self.assertIn("const EXAMPLE_GROUP_DELAY_MS = 2000;", app_js)
        self.assertIn(
            "addRepeatedEnglishWithChinese(queue, segments.example_1_en, "
            "word?.example_1_en, segments.example_1_zh, word?.example_1_zh, "
            "repeatCount);",
            app_js,
        )
        self.assertIn(
            "addRepeatedEnglishWithChinese(queue, segments.example_2_en, "
            "word?.example_2_en, segments.example_2_zh, word?.example_2_zh, "
            "repeatCount, EXAMPLE_GROUP_DELAY_MS);",
            app_js,
        )
        self.assertIn("const groupStartIndex = queue.length;", app_js)
        self.assertIn("queue[groupStartIndex].delayMs = startDelayMs;", app_js)


if __name__ == "__main__":
    unittest.main()
