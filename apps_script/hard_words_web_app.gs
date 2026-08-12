const SHEET_NAME = "HardWords";
const IMPORTANT_EXAMPLES_SHEET_NAME = "ImportantExamples";
const IMPORTANT_EXAMPLE_HEADERS = [
  "example_key", "source_chapter", "source_id", "example_number",
  "word", "example_en", "important", "updated_at",
];
const PRACTICE_STATS_WORD = "__EVD_PRACTICE_STATS__";
const PRACTICE_STATS_STATUS = "practice_stats";
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

  if (payload.action === "important_example") {
    const rowNumber = upsertImportantExample(payload);
    return jsonResponse({ ok: true, rowNumber, workflow: { ok: false, skipped: true } });
  }

  const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_NAME);
  if (!sheet) {
    return jsonResponse({ ok: false, error: `Missing sheet: ${SHEET_NAME}` });
  }

  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  if (payload.status === PRACTICE_STATS_STATUS && payload.word === PRACTICE_STATS_WORD) {
    payload.note = mergePracticeStateNote(sheet, headers, payload.note);
  }
  const row = headers.map((header) => payload[header] || "");
  const rowNumber = upsertHardWordRow(sheet, headers, row, payload.word);
  let workflow = { ok: false };
  if (payload.status !== PRACTICE_STATS_STATUS) {
    try {
      workflow = triggerDailyVocabularyWorkflow(true);
    } catch (error) {
      workflow = { ok: false, error: String(error) };
      console.error(error);
    }
  } else {
    workflow = { ok: false, skipped: true };
  }

  return jsonResponse({ ok: true, rowNumber, workflow });
}

function doGet(e) {
  const props = PropertiesService.getScriptProperties();
  const action = e && e.parameter ? e.parameter.action : "";
  if (action === "client_state") {
    const passcode = props.getProperty(PROP_PASSCODE);
    const suppliedPasscode = e && e.parameter ? e.parameter.passcode : "";
    const callback = e && e.parameter ? e.parameter.callback : "";
    if (!passcode || suppliedPasscode !== passcode) {
      return javascriptResponse({ ok: false, error: "Invalid passcode." }, callback);
    }
    return javascriptResponse(buildClientState(), callback);
  }
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

function upsertImportantExample(payload) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const sheet = getOrCreateImportantExamplesSheet();
    const exampleKey = String(payload.example_key || "").trim();
    if (!exampleKey) {
      throw new Error("Missing example_key.");
    }
    const values = IMPORTANT_EXAMPLE_HEADERS.map((header) => (
      payload[header] == null ? "" : payload[header]
    ));
    const lastRow = sheet.getLastRow();
    if (lastRow >= 2) {
      const keys = sheet.getRange(2, 1, lastRow - 1, 1).getValues();
      const existingIndex = keys.findIndex((value) => String(value[0]) === exampleKey);
      if (existingIndex >= 0) {
        const rowNumber = existingIndex + 2;
        sheet.getRange(rowNumber, 1, 1, values.length).setValues([values]);
        return rowNumber;
      }
    }
    sheet.appendRow(values);
    return sheet.getLastRow();
  } finally {
    lock.releaseLock();
  }
}

function getOrCreateImportantExamplesSheet() {
  const spreadsheet = SpreadsheetApp.getActive();
  let sheet = spreadsheet.getSheetByName(IMPORTANT_EXAMPLES_SHEET_NAME);
  if (!sheet) {
    sheet = spreadsheet.insertSheet(IMPORTANT_EXAMPLES_SHEET_NAME);
    sheet.getRange(1, 1, 1, IMPORTANT_EXAMPLE_HEADERS.length)
      .setValues([IMPORTANT_EXAMPLE_HEADERS]);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function buildClientState() {
  const hardWordsSheet = SpreadsheetApp.getActive().getSheetByName(SHEET_NAME);
  const importantSheet = SpreadsheetApp.getActive().getSheetByName(IMPORTANT_EXAMPLES_SHEET_NAME);
  return {
    ok: true,
    api_version: 2,
    important_examples: readImportantExamples(importantSheet),
    practice_state: readPracticeState(hardWordsSheet),
    server_time: new Date().toISOString(),
  };
}

function readImportantExamples(sheet) {
  if (!sheet || sheet.getLastRow() < 2) {
    return {};
  }
  const rows = sheetRowsAsObjects(sheet);
  return rows.reduce((records, row) => {
    const exampleKey = String(row.example_key || "").trim();
    if (!exampleKey) {
      return records;
    }
    records[exampleKey] = {
      example_key: exampleKey,
      source_chapter: String(row.source_chapter || ""),
      source_id: String(row.source_id || ""),
      example_number: Number(row.example_number) === 2 ? 2 : 1,
      word: String(row.word || ""),
      example_en: String(row.example_en || ""),
      important: String(row.important).toLowerCase() === "true",
      updated_at: String(row.updated_at || ""),
    };
    return records;
  }, {});
}

function readPracticeState(sheet) {
  if (!sheet || sheet.getLastRow() < 2) {
    return {};
  }
  const row = sheetRowsAsObjects(sheet).find((item) => (
    String(item.word || "") === PRACTICE_STATS_WORD
    && String(item.status || "").toLowerCase() === PRACTICE_STATS_STATUS
  ));
  return parseJsonObject(row ? row.note : "");
}

function sheetRowsAsObjects(sheet) {
  const values = sheet.getDataRange().getValues();
  const headers = values[0].map(String);
  return values.slice(1).map((row) => headers.reduce((record, header, index) => {
    record[header] = row[index];
    return record;
  }, {}));
}

function mergePracticeStateNote(sheet, headers, incomingNote) {
  const incoming = parseJsonObject(incomingNote);
  const existingRow = findHardWordRow(sheet, headers, PRACTICE_STATS_WORD);
  const noteColumn = headers.indexOf("note");
  const existing = existingRow > 0 && noteColumn >= 0
    ? parseJsonObject(sheet.getRange(existingRow, noteColumn + 1).getValue())
    : {};
  const records = {};
  [existing.r, incoming.r].forEach((items) => {
    (Array.isArray(items) ? items : []).forEach((item) => {
      if (!Array.isArray(item) || item.length < 4 || !String(item[0] || "").trim()) {
        return;
      }
      const key = normalizeWord(item[0]);
      const current = records[key];
      if (!current) {
        records[key] = item.slice(0, 4);
        return;
      }
      current[1] = Math.max(Number(current[1]) || 0, Number(item[1]) || 0);
      current[2] = Math.max(Number(current[2]) || 0, Number(item[2]) || 0);
      current[3] = String(current[3] || "") >= String(item[3] || "") ? current[3] : item[3];
    });
  });
  const existingSettingsAt = String(existing.su || "");
  const incomingSettingsAt = String(incoming.su || "");
  const useIncomingSettings = incomingSettingsAt >= existingSettingsAt;
  return JSON.stringify({
    v: 2,
    u: new Date().toISOString(),
    r: Object.keys(records).sort().map((key) => records[key]),
    s: useIncomingSettings ? (incoming.s || {}) : (existing.s || {}),
    su: useIncomingSettings ? incomingSettingsAt : existingSettingsAt,
  });
}

function findHardWordRow(sheet, headers, word) {
  const wordColumn = headers.indexOf("word") + 1;
  if (wordColumn <= 0 || sheet.getLastRow() < 2) {
    return 0;
  }
  const words = sheet.getRange(2, wordColumn, sheet.getLastRow() - 1, 1).getValues();
  const index = words.findIndex((value) => normalizeWord(value[0]) === normalizeWord(word));
  return index >= 0 ? index + 2 : 0;
}

function parseJsonObject(value) {
  try {
    const parsed = JSON.parse(String(value || "{}"));
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch (error) {
    return {};
  }
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

function javascriptResponse(value, callback) {
  const safeCallback = String(callback || "");
  if (!/^[A-Za-z_$][0-9A-Za-z_$]*$/.test(safeCallback)) {
    return jsonResponse(value);
  }
  return ContentService
    .createTextOutput(`${safeCallback}(${JSON.stringify(value)});`)
    .setMimeType(ContentService.MimeType.JAVASCRIPT);
}
