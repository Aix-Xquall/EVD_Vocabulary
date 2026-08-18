# EVD Daily Vocabulary

## CSV vocabulary folder

Put vocabulary CSV files in `vocabulary/`. GitHub Actions watches this folder, so future CSV additions or edits there will be included in the daily site update.

The loader expands these engineering abbreviations for display:

- `MIL-STD-461` -> `Military Standard 461 (MIL-STD-461)`
- `EMC` -> `Electromagnetic Compatibility (EMC)`
- `EMS` -> `Electromagnetic Susceptibility (EMS)`
- `E3` -> `Electromagnetic Environmental Effects (E3)`
- `EPDS` -> `Electronic Power Distribution System (EPDS)`

For audio, the same terms are spoken as the full English phrase. Chinese columns keep abbreviations such as `EMC` and `EMS` unchanged, so Chinese TTS reads the abbreviation letters instead of the expanded English phrase.

## Hard words sync

The site shows a separate hard words chapter named `未熟記單字練習`, even when it currently has zero words. The repo uses `vocabulary/hard_words.csv` as the local snapshot, while Google Sheets and Google Apps Script provide cross-device writes from phone or PC. Newly added hard words appear first. A word can also be marked `已熟記`; its English word and English examples play twice, while other words use the configured repeat count.

Daily practice uses an English example cloze question with the Chinese example as a hint. Answers ignore letter case and outer whitespace, but spelling and internal spaces must match exactly.

Google Sheet columns should include the normal vocabulary columns:

```csv
id,word,pronunciation,chinese_meaning,example_1_en,example_1_zh,example_2_en,example_2_zh,category,difficulty,review_count,last_review_date
```

Optional tracking columns:

```csv
source_chapter,source_id,added_at,status,note
```

Only blank `status` or `active` rows are published. `removed` rows stay in the sheet but are not shown.

GitHub repository secrets for this feature:

```text
HARD_WORDS_SHEET_CSV_URL
HARD_WORDS_READ_TOKEN
HARD_WORDS_WRITE_URL
```

`HARD_WORDS_SHEET_CSV_URL` is the CSV export or Apps Script read URL. `HARD_WORDS_READ_TOKEN` is optional. `HARD_WORDS_WRITE_URL` is the Apps Script Web App URL used by the browser when you tap `加入未熟記單字練習` or `從未熟記單字移除`.

Recommended Apps Script deployment:

- Execute as: `Me`
- Who has access: `Anyone`
- Validate a simple passcode in the script before writing to the sheet.

Do not put GitHub tokens, Azure keys, LINE tokens, or Google account credentials in the public web page.

Use the maintained Apps Script template in `apps_script/hard_words_web_app.gs`. Copy it into your Google Apps Script project, then set these Script Properties:

```text
HARD_WORDS_PASSCODE
HARD_WORDS_READ_TOKEN
GITHUB_TOKEN
GITHUB_OWNER=Aix-Xquall
GITHUB_REPO=EVD_Vocabulary
GITHUB_WORKFLOW_FILE=daily-vocabulary.yml
GITHUB_REF=main
```

Use the Apps Script Web App URL with `readToken` for the repository secret:

```text
HARD_WORDS_SHEET_CSV_URL=https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec?readToken=YOUR_READ_TOKEN
HARD_WORDS_READ_TOKEN=YOUR_READ_TOKEN
```

`GITHUB_TOKEN` should be a fine-grained GitHub token that can access only this repository. Give it `Actions: Read and write` permission so Apps Script can call `workflow_dispatch`. Keep the token only in Apps Script Properties; never paste it into `web/app.js`, `latest.json`, GitHub Pages, or any public file.

After each successful hard-word or mastered-word write, the Apps Script template calls the GitHub Actions API to run `Daily Vocabulary`. That workflow refreshes `vocabulary/hard_words.csv`, regenerates `latest.json`, and deploys GitHub Pages.

Hard-word and mastered-word refreshes pass `skip_line_notification=true`, so they update the site without sending a LINE message. Scheduled runs send LINE only when new vocabulary is detected. For a one-time test or completion message, manually run `Daily Vocabulary` with `force_line_notification=true`.

After changing or redeploying the Apps Script Web App, run `Daily Vocabulary` once from GitHub Actions or push a normal repo change so the published site picks up the latest hard-words settings and snapshot.

Duplicate entries are skipped by the normalized `word` field inside each normal chapter. The hard words chapter can intentionally repeat a word that also exists in a normal chapter, but duplicate words inside `hard_words.csv` are collapsed.

## Practice statistics

The site records one practice after a word finishes playing with the current example setting. Each additional completed cycle caused by `重複目前單字` also increments that word's repeat count. Open `練習統計` after `每日練習` to switch between the most-practiced and most-repeated rankings; the player also shows counts for the current word.

Statistics and player settings are saved locally first, then synchronized directly through the existing Google Sheet and Apps Script channel. The synchronized settings include the selected chapter, chapter loop, current-word repeat, example playback, English voice, English playback rate, English repeat count, and learning colors. On a new device, select `同步統計` or `同步設定` once and enter the existing `HARD_WORDS_PASSCODE`. Later changes synchronize automatically. Offline changes remain in the browser and are retried later.

## Example references

Every English example has a source annotation in `annotations/example_sources.csv`. The generated Markdown and website show the reference document, section, page, and one of these attribution labels:

- `原文摘錄`: the example matches document text.
- `改寫自`: the sentence is adapted from the cited section.
- `主題參考`: the section supports the engineering term or concept, but is not the sentence source.
- `自編例句`: no sufficiently relevant reference section was found; this also applies to travel conversation examples.

Validate complete coverage without generating audio or sending LINE:

```powershell
python example_source_analyzer.py validate
```

`hard_words.csv` remains a Google Sheet snapshot. When a hard word still exists in a formal chapter, the generated site uses the formal chapter's current wording, Chinese translation, examples, and references so an older snapshot does not restore stale text.

## Important examples and direct synchronization

Each English example has an `重要` checkbox. Important-example records use the word and example number as a stable key, are saved locally immediately, and are written to an `ImportantExamples` Google Sheet tab. The Apps Script creates that tab and its headers automatically on the first write.

The browser reads current important examples, practice statistics, and player settings directly from Apps Script when the page opens, returns to the foreground, reconnects to the network, or performs a manual sync. Each important-example row has its own `updated_at` timestamp, so a newer change on one device does not overwrite a newer change from another device. Offline changes remain queued in `localStorage` and retry when connectivity returns.

After pulling this version, update the existing Apps Script project with the complete contents of `apps_script/hard_words_web_app.gs`, save it, and deploy a new Web App version. Keep the existing deployment URL and Script Properties. Until that deployment is updated, important-example changes stay safely on the current device and the page displays a reminder instead of writing an incompatible row to `HardWords`.

Practice statistics and settings now retry after 5 seconds with a 15-second minimum interval. Apps Script merges counters using the larger value and keeps the settings with the newer timestamp. These direct state writes no longer trigger GitHub Actions; Actions remain responsible for vocabulary, audio, and static-site deployment.

## 目前模式

此專案目前採用「章節化 + 分段音訊 + 前端播放佇列」：

- `*.csv` 每個檔案會成為網頁上的一個章節。
- 網頁可在上方切換章節，播放目前單字或整個章節。
- 音訊不再只依賴單一完整 MP3，而是使用 `output/audio/segments/` 下的分段 MP3。
- 分段 MP3 以文字內容、語言、voice 與語速產生 hash 檔名，已有相同內容時會重用，降低 Azure Speech Free (F0) 用量。
- 英文語速可在網頁調整，預設 1.0x；中文播放固定 1.0x。
- 英文單字與例句預設重複 5 次，可在網頁調整為 1 到 5 次；中文翻譯只播放 1 次。
- 例句 1（含中文與英文重複）完成後等待 2 秒，再播放例句 2；中文後的英文重複仍間隔 1.5 秒。
- 章節模式不會自動更新 `review_count` 與 `last_review_date`，避免每日排程把所有章節都標記為已複習。

每日航太 / 航電 / EMC 工程英文學習工具。

這個專案會從同一個資料夾內的 `*.csv` 讀取單字，將每個 CSV 當成一個章節，產生：

- Markdown 學習稿
- 每個單字一個 MP3
- 一個完整 MP3
- 給網頁使用的 `latest.json`
- 可部署到 GitHub Pages 的每日練習網頁
- 可選的 LINE 個人通知

## 資料格式

CSV 必須包含以下欄位：

```text
id
word
pronunciation
chinese_meaning
example_1_en
example_1_zh
example_2_en
example_2_zh
category
difficulty
review_count
last_review_date
```

新增 CSV 時請使用上方欄位名稱，並放在 `vocabulary/` 資料夾。

## 每日選字規則

程式會優先選：

1. `review_count` 較低的單字
2. `last_review_date` 較舊的單字，空白視為最久沒複習
3. `difficulty` 較高的單字
4. 同分時用日期做穩定排序，避免每天完全一樣

產生檔案後，程式才會更新原始 CSV 的：

- `review_count`
- `last_review_date`

## 本機執行

在 Windows 11 + VS Code 中：

```powershell
cd D:\Dropbox\English\projects\EVD_Vocabulary
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

如果只想測試資料、Markdown、JSON、網頁，不產生音訊：

```powershell
python main.py --skip-audio --skip-line --no-update-review
```

正式產生每日內容：

```powershell
python main.py
```

## Azure Speech 設定

產生 MP3 需要 Azure AI Speech。

請設定環境變數：

```powershell
$env:AZURE_SPEECH_KEY="你的 Azure Speech key"
$env:AZURE_SPEECH_REGION="你的 Azure region"
```

可選設定：

```powershell
$env:EVD_DAILY_WORD_COUNT="20"
$env:EVD_SPEECH_RATE="0%"
$env:EVD_INCLUDE_CHINESE_AUDIO="true"
$env:EVD_REPEAT_EACH_WORD="true"
$env:EVD_OUTPUT_DIR="D:\Dropbox\English\projects\EVD_Vocabulary\output"
$env:EVD_ENGLISH_VOICE="en-US-JennyNeural"
$env:EVD_CHINESE_VOICE="zh-TW-HsiaoChenNeural"
```

## Google Cloud Text-to-Speech setup

Google TTS is supported as the current default provider. Existing Azure MP3 segment files are not overwritten; Google uses separate content-addressed segment file names.

Before local testing:

1. Create or select a Google Cloud project.
2. Enable `Cloud Text-to-Speech API`.
3. To report actual monthly usage, also enable `Cloud Monitoring API`.
4. Link Billing if Google asks for it. Confirm this step carefully because it involves payment settings, even when you plan to stay inside the free tier.
5. Create a Service Account and download its JSON key.
6. Grant the Service Account `Monitoring Viewer` if you want LINE to show Google TTS usage from Google Cloud Monitoring.
7. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Local environment example:

```powershell
$env:EVD_TTS_PROVIDER="google"
$env:GOOGLE_APPLICATION_CREDENTIALS="D:\secure\google-tts-key.json"
$env:GOOGLE_CLOUD_PROJECT_ID="your-google-cloud-project-id"
$env:GOOGLE_ENGLISH_VOICE="en-US-Neural2-J"
$env:GOOGLE_MALE_VOICE="en-US-Neural2-J"
$env:GOOGLE_FEMALE_VOICE="en-US-Wavenet-H"
$env:GOOGLE_CHINESE_VOICE="cmn-TW-Wavenet-A"
$env:EVD_SPEECH_RATE="-20%"
python main.py --skip-line --no-update-review
```

For GitHub Actions, add this Repository Secret:

```text
GOOGLE_TTS_CREDENTIALS_JSON
```

Paste the full Service Account JSON key as the secret value. Never commit the JSON key to the repo, and never put it under `web/` or `output/`.

Add these Repository Variables:

```text
EVD_TTS_PROVIDER=google
GOOGLE_ENGLISH_VOICE=en-US-Neural2-J
GOOGLE_MALE_VOICE=en-US-Neural2-J
GOOGLE_FEMALE_VOICE=en-US-Wavenet-H
GOOGLE_CHINESE_VOICE=cmn-TW-Wavenet-A
GOOGLE_CLOUD_PROJECT_ID=your-google-cloud-project-id
```

If `EVD_TTS_PROVIDER` is not set, the project defaults to Google TTS. The published site provides `en-US-Neural2-J` (male) and `en-US-Wavenet-H` (female), while Chinese uses one shared `cmn-TW-Wavenet-A` file. English speed is still controlled by `EVD_SPEECH_RATE=-20%`, which maps to 0.8x for Google. Chinese speed stays at 1.0x. To switch back to Azure Free F0, set `EVD_TTS_PROVIDER=azure`.

## Manual ChatGPT tense analysis

The site shows each English example tense and bolds the words that express the tense. Reviewed results are stored in `annotations/tense_annotations.csv`; the daily workflow does not call OpenAI or require an API key.

Modal verbs are derived automatically from each English example. A reviewed
`特殊句型/需確認` annotation that contains a modal is displayed only as its
concrete modal and base verb, such as `情態動詞：should + 原形動詞：review`.
The twelve tense labels use the standard `時態：公式` display format.

When new vocabulary CSV files are added:

1. Export only examples that do not have annotations:

   ```powershell
   python tense_analyzer.py export-pending
   ```

2. Upload `tense_review/pending_tense_examples.csv` to ChatGPT and use the prompt in `docs/tense-analysis-prompt.md`.
3. Download the completed CSV without changing its headers or original English sentences.
4. Validate and merge the completed file:

   ```powershell
   python tense_analyzer.py import C:\path\to\completed_tense_examples.csv
   ```

5. Confirm every current example is covered:

   ```powershell
   python tense_analyzer.py validate --require-complete
   ```

The importer rejects unknown sentences, invalid tense names, confidence values outside `0` to `1`, malformed JSON, and highlighted text that is not an exact substring of the English example. Validation runs three passes: data integrity and coverage, display-rule consistency, and an independent check of explicit auxiliary-verb markers against the reviewed tense. Temporary files under `tense_review/` are ignored by Git. GitHub Actions also runs the complete validation before deployment.

## TTS free quota reporting

The LINE message reports remaining TTS quota as follows:

- Google Cloud Text-to-Speech: the project first tries Google Cloud Monitoring `serviceruntime.googleapis.com/quota/rate/net_usage`, then falls back to `output/data/tts_usage.json` when Monitoring is not configured or not available.
- Azure Free F0: the project can query Azure Monitor `SynthesizedCharacters`, then calculates remaining free quota from `500,000` characters per month.
- LINE Messaging API: the project queries LINE quota and monthly consumption directly.

Google Cloud Quotas API can show quota limit metadata, for example `https://cloudquotas.googleapis.com/v1/projects/PROJECT_ID/locations/global/services/texttospeech.googleapis.com/quotaInfos`. It is not used as the primary source for monthly used characters because Cloud Monitoring exposes the actual quota usage metric.

Optional Repository Variables:

```text
EVD_GOOGLE_TTS_FREE_LIMIT=1000000
EVD_AZURE_SPEECH_FREE_LIMIT=500000
GOOGLE_CLOUD_PROJECT_ID=your-google-cloud-project-id
GOOGLE_TTS_QUOTA_METRIC=texttospeech.googleapis.com/characters
EVD_GOOGLE_TTS_FREE_REMAINING=900000 characters
EVD_AZURE_SPEECH_FREE_REMAINING=45000 characters
```

`EVD_GOOGLE_TTS_FREE_REMAINING` and `EVD_AZURE_SPEECH_FREE_REMAINING` are fallback text only. They are used when automatic reporting is not available.

To enable Azure Monitor reporting, create an Azure app registration or service principal with read access to the Speech resource. This involves Azure identity and permission setup, so confirm the scope carefully before granting access. Add these Repository Secrets:

```text
AZURE_TENANT_ID
AZURE_CLIENT_ID
AZURE_CLIENT_SECRET
AZURE_SUBSCRIPTION_ID
AZURE_SPEECH_RESOURCE_GROUP
AZURE_SPEECH_RESOURCE_NAME
```

If these Azure Monitor secrets are missing, the daily workflow still runs. The LINE message will show the fallback value or `未設定 Azure Monitor 權限`.

## 輸出結構

```text
output/
  audio/
    YYYY-MM-DD/
      001_word.mp3
      002_word.mp3
    YYYY-MM-DD_daily_vocabulary.mp3
  data/
    YYYY-MM-DD_daily_vocabulary.json
    latest.json
    tts_usage.json
  scripts/
    YYYY-MM-DD_daily_vocabulary.md
  index.html
  app.js
  styles.css
```

GitHub Pages 會部署 `output/` 這個資料夾。

## 網頁播放

網頁可以線上播放音訊，不需要手動下載 MP3。

瀏覽器通常會阻擋「打開網頁就直接出聲音」，所以使用方式是：

1. 點 LINE 裡的網頁連結
2. 按一次「開始播放」
3. 後續 20 個單字會自動依序播放

## GitHub Pages

建議流程：

1. 先在本機確認 `python main.py --skip-audio --skip-line --no-update-review` 可產生輸出
2. 在 GitHub 建立 public repo
3. 把整個 `EVD_Vocabulary` 專案推上 GitHub
4. 到 repo 的 Settings → Pages
5. Source 選 GitHub Actions
6. 到 Actions 手動執行 `Daily Vocabulary`

## GitHub Secrets

在 GitHub repo 的 Settings → Secrets and variables → Actions 新增：

Secrets:

```text
AZURE_SPEECH_KEY
AZURE_SPEECH_REGION
AZURE_TENANT_ID
AZURE_CLIENT_ID
AZURE_CLIENT_SECRET
AZURE_SUBSCRIPTION_ID
AZURE_SPEECH_RESOURCE_GROUP
AZURE_SPEECH_RESOURCE_NAME
LINE_CHANNEL_ACCESS_TOKEN
LINE_USER_ID
```

Variables:

```text
EVD_SITE_URL
```

`EVD_SITE_URL` 範例：

```text
https://你的帳號.github.io/你的repo名稱/
```

## LINE 個人通知

LINE Notify 已經在 2025-03-31 結束服務，所以這裡使用 LINE Messaging API。

你需要：

1. 建立 LINE 官方帳號
2. 在 LINE Developers 建立 Messaging API channel
3. 取得 channel access token
4. 取得自己的 LINE user ID
5. 把 token 和 user ID 放到 GitHub Secrets

注意：`LINE_USER_ID` 不是你的 LINE 顯示 ID。它通常從 LINE Developers Console 的個人資訊或 webhook event 取得。

## 常用指令

測試：

```powershell
python -m unittest discover -s tests -v
```

產生指定日期，但不更新 CSV：

```powershell
python main.py --date 2026-06-17 --skip-audio --skip-line --no-update-review
```

產生指定日期並更新 CSV：

```powershell
python main.py --date 2026-06-17
```
