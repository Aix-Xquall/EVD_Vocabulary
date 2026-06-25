const SHEET_NAME = "HardWords";
const PROP_PASSCODE = "HARD_WORDS_PASSCODE";
const PROP_GITHUB_TOKEN = "GITHUB_TOKEN";
const PROP_GITHUB_OWNER = "GITHUB_OWNER";
const PROP_GITHUB_REPO = "GITHUB_REPO";
const PROP_GITHUB_WORKFLOW_FILE = "GITHUB_WORKFLOW_FILE";
const PROP_GITHUB_REF = "GITHUB_REF";
const PROP_READ_TOKEN = "HARD_WORDS_READ_TOKEN";

function doPost(e) {
  const payload = readPostPayload(e);
  if (payload.error) {
    return jsonResponse({ ok: false, error: payload.error });
  }
  const props = PropertiesService.getScriptProperties();
  const passcode = props.getProperty(PROP_PASSCODE);
  if (!passcode || payload.passcode !== passcode) {
    return jsonResponse({ ok: false, error: "Invalid passcode." });
  }

  const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_NAME);
  if (!sheet) {
    return jsonResponse({ ok: false, error: `Missing sheet: ${SHEET_NAME}` });
  }

  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const row = headers.map((header) => payload[header] || "");
  const rowNumber = upsertHardWordRow(sheet, headers, row, payload.word);
  let workflow = { ok: false };
  try {
    workflow = triggerDailyVocabularyWorkflow(true);
  } catch (error) {
    workflow = { ok: false, error: String(error) };
    console.error(error);
  }

  return jsonResponse({ ok: true, rowNumber, workflow });
}

function doGet(e) {
  const props = PropertiesService.getScriptProperties();
  const expectedToken = props.getProperty(PROP_READ_TOKEN) || props.getProperty("READ_TOKEN");
  const readToken = e && e.parameter ? e.parameter.readToken : "";
  if (!expectedToken) {
    return jsonResponse({ ok: false, error: "Missing HARD_WORDS_READ_TOKEN script property." });
  }
  if (readToken !== expectedToken) {
    return jsonResponse({ ok: false, error: "Invalid read token." });
  }

  const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_NAME);
  if (!sheet) {
    return jsonResponse({ ok: false, error: `Missing sheet: ${SHEET_NAME}` });
  }

  return csvResponse(sheetToCsv(sheet));
}

function readPostPayload(e) {
  if (!e || !e.postData || !e.postData.contents) {
    return {
      error: "Missing POST body. Deploy this script as a Web App and call the Web App URL, or run testTriggerDailyVocabularyWorkflow() to test GitHub Actions dispatch manually.",
    };
  }
  return JSON.parse(e.postData.contents || "{}");
}

function testTriggerDailyVocabularyWorkflow() {
  return triggerDailyVocabularyWorkflow(false);
}

function upsertHardWordRow(sheet, headers, row, word) {
  const wordColumn = headers.indexOf("word") + 1;
  if (wordColumn <= 0 || !word) {
    sheet.appendRow(row);
    return sheet.getLastRow();
  }

  const normalizedWord = normalizeWord(word);
  const lastRow = sheet.getLastRow();
  if (lastRow >= 2) {
    const words = sheet.getRange(2, wordColumn, lastRow - 1, 1).getValues();
    const existingIndex = words.findIndex((value) => normalizeWord(value[0]) === normalizedWord);
    if (existingIndex >= 0) {
      const rowNumber = existingIndex + 2;
      sheet.getRange(rowNumber, 1, 1, row.length).setValues([row]);
      return rowNumber;
    }
  }

  sheet.appendRow(row);
  return sheet.getLastRow();
}

function triggerDailyVocabularyWorkflow(skipLineNotification) {
  const props = PropertiesService.getScriptProperties();
  const token = props.getProperty(PROP_GITHUB_TOKEN);
  const owner = props.getProperty(PROP_GITHUB_OWNER) || "Aix-Xquall";
  const repo = props.getProperty(PROP_GITHUB_REPO) || "EVD_Vocabulary";
  const workflowFile = props.getProperty(PROP_GITHUB_WORKFLOW_FILE) || "daily-vocabulary.yml";
  const ref = props.getProperty(PROP_GITHUB_REF) || "main";
  if (!token) {
    throw new Error("Missing GITHUB_TOKEN script property.");
  }

  const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${encodeURIComponent(workflowFile)}/dispatches`;
  const options = {
    method: "post",
    contentType: "application/json",
    muteHttpExceptions: true,
    headers: {
      "Authorization": `Bearer ${token}`,
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    payload: JSON.stringify({
      ref,
      inputs: {
        skip_line_notification: skipLineNotification ? "true" : "false",
      },
    }),
  };
  const response = UrlFetchApp.fetch(url, options);
  const status = response.getResponseCode();
  if (status < 200 || status >= 300) {
    throw new Error(`GitHub workflow dispatch failed: ${status} ${response.getContentText()}`);
  }
  return { ok: true, status };
}

function normalizeWord(value) {
  return String(value || "").trim().toLowerCase();
}

function sheetToCsv(sheet) {
  const values = sheet.getDataRange().getValues();
  return values.map((row) => row.map(csvCell).join(",")).join("\n") + "\n";
}

function csvCell(value) {
  const text = String(value == null ? "" : value);
  if (/[",\r\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function csvResponse(value) {
  return ContentService
    .createTextOutput(value)
    .setMimeType(ContentService.MimeType.CSV);
}

function jsonResponse(value) {
  return ContentService
    .createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}
