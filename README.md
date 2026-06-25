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

The site shows a separate hard words chapter named `未熟記單字練習`, even when it currently has zero words. The repo uses `vocabulary/hard_words.csv` as the local snapshot, while Google Sheets and Google Apps Script provide cross-device writes from phone or PC.

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
GITHUB_TOKEN
GITHUB_OWNER=Aix-Xquall
GITHUB_REPO=EVD_Vocabulary
GITHUB_WORKFLOW_FILE=daily-vocabulary.yml
GITHUB_REF=main
```

`GITHUB_TOKEN` should be a fine-grained GitHub token that can access only this repository. Give it `Actions: Read and write` permission so Apps Script can call `workflow_dispatch`. Keep the token only in Apps Script Properties; never paste it into `web/app.js`, `latest.json`, GitHub Pages, or any public file.

After each successful hard-word write, the Apps Script template calls the GitHub Actions API to run `Daily Vocabulary`. That workflow refreshes `vocabulary/hard_words.csv`, regenerates `latest.json`, deploys GitHub Pages, and sends the normal LINE notification.

Duplicate entries are skipped by the normalized `word` field inside each normal chapter. The hard words chapter can intentionally repeat a word that also exists in a normal chapter, but duplicate words inside `hard_words.csv` are collapsed.

## 目前模式

此專案目前採用「章節化 + 分段音訊 + 前端播放佇列」：

- `*.csv` 每個檔案會成為網頁上的一個章節。
- 網頁可在上方切換章節，播放目前單字或整個章節。
- 音訊不再只依賴單一完整 MP3，而是使用 `output/audio/segments/` 下的分段 MP3。
- 分段 MP3 以文字內容、語言、voice 與語速產生 hash 檔名，已有相同內容時會重用，降低 Azure Speech Free (F0) 用量。
- 英文語速可在網頁調整，預設 0.8x；中文播放固定 1.0x。
- 英文例句預設重複 3 次，可在網頁調整為 1 到 5 次；中文翻譯只播放 1 次。
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

請參考 `sample vocabulary.csv`。

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
