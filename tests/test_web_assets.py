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

    def test_web_player_exposes_chapters_and_example_repeat_controls(self):
        index_html = (PROJECT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="chapterTabs"', index_html)
        self.assertIn('id="exampleRepeatCount"', index_html)
        self.assertIn('min="1"', index_html)
        self.assertIn('max="5"', index_html)
        self.assertIn('value="3"', index_html)
        self.assertIn("DEFAULT_EXAMPLE_REPEAT_COUNT = 3", app_js)
        self.assertIn("buildWordQueue", app_js)
        self.assertIn("buildChapterQueue", app_js)
        self.assertIn('segment.language === "en" ? state.playbackRate : 1', app_js)
        self.assertIn("speechSynthesis", app_js)
        self.assertIn("SpeechSynthesisUtterance", app_js)

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
        self.assertIn("container.scrollTop =", app_js)
        self.assertIn("activeButton.offsetTop - container.clientHeight / 2 + activeButton.clientHeight / 2", app_js)

    def test_browser_speech_fallback_uses_di_pronunciation_for_ground_character(self):
        app_js = (PROJECT_DIR / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("speechTextForAudio", app_js)
        self.assertIn('.replaceAll("地", "第")', app_js)
        self.assertIn("SpeechSynthesisUtterance(speechTextForAudio(segment.text, segment.language))", app_js)


if __name__ == "__main__":
    unittest.main()
