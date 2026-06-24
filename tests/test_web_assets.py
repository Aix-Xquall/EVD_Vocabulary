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
        self.assertIn("speechSynthesis", app_js)
        self.assertIn("SpeechSynthesisUtterance", app_js)

    def test_word_and_examples_share_the_same_repeat_behavior(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn(
            'addRepeatedEnglishWithChinese(queue, segments.word, word?.word, segments.meaning, word?.chinese_meaning)',
            app_js,
        )
        self.assertIn("for (let count = 1; count < state.englishRepeatCount; count += 1)", app_js)
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

    def test_active_word_is_centered_inside_scrollable_word_list(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("scrollActiveWordIntoView", app_js)
        self.assertIn("container.getBoundingClientRect()", app_js)
        self.assertIn("activeButton.getBoundingClientRect()", app_js)
        self.assertIn("container.scrollTop + activeRect.top - containerRect.top", app_js)
        self.assertIn("Math.max(0, targetTop)", app_js)
        self.assertIn("container.scrollTop =", app_js)
        self.assertNotIn("activeButton.offsetTop - container.clientHeight / 2", app_js)

    def test_browser_speech_fallback_uses_di_pronunciation_for_ground_character(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("speechTextForAudio", app_js)
        self.assertIn('.replaceAll("地", "第")', app_js)
        self.assertIn("SpeechSynthesisUtterance(speechTextForAudio(segment.text, segment.language))", app_js)

    def test_browser_speech_fallback_expands_known_english_abbreviations(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("expandKnownAbbreviationsForSpeech", app_js)
        self.assertIn("Electromagnetic Compatibility", app_js)
        self.assertIn("Electromagnetic Susceptibility", app_js)
        self.assertIn("Military Standard 461", app_js)

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

    def test_hard_words_chapter_count_updates_immediately_after_toggle(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("chapterWordCount(chapter)", app_js)
        self.assertIn("function hardWordsChapter()", app_js)
        self.assertIn("function applyHardWordLocalState(word, status)", app_js)
        self.assertIn("applyHardWordLocalState(word, nextStatus)", app_js)
        self.assertIn("chapter.words.push({ ...word })", app_js)
        self.assertIn("chapter.words.splice(existingIndex, 1)", app_js)
        self.assertIn("chapter.word_count = chapter.words.length", app_js)

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

    def test_chapter_playback_uses_segment_queue_with_wake_lock_controls(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("const chapterQueue = buildChapterQueue()", app_js)
        self.assertIn("playQueue(chapterQueue, true)", app_js)
        self.assertNotIn("chapter.chapter_audio", app_js)
        self.assertNotIn('playDirectAudio(chapter.chapter_audio, "mixed")', app_js)


if __name__ == "__main__":
    unittest.main()
