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


if __name__ == "__main__":
    unittest.main()
