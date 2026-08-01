const assert = require("node:assert/strict");
const test = require("node:test");

const {
  buildClozeCandidates,
  findLiteralHighlightRanges,
  findTargetPhraseMatches,
  incrementPracticeRecord,
  isCorrectClozeAnswer,
  repeatCountForWord,
  sanitizePronunciation,
} = require("../web/learning_helpers.js");

test("mastered words use configured repetitions when examples are included", () => {
  assert.equal(repeatCountForWord(true, 5, false), 2);
  assert.equal(repeatCountForWord(true, 5, true), 5);
  assert.equal(repeatCountForWord(false, 5, true), 5);
});

test("practice records count completed words and extra repeat-current cycles", () => {
  const first = incrementPracticeRecord(null, "impedance", false, "2026-07-31T01:00:00Z");
  const repeated = incrementPracticeRecord(first, "impedance", true, "2026-07-31T01:01:00Z");

  assert.deepEqual(first, {
    word: "impedance",
    practice_count: 1,
    repeat_current_count: 0,
    last_practiced_at: "2026-07-31T01:00:00Z",
  });
  assert.deepEqual(repeated, {
    word: "impedance",
    practice_count: 2,
    repeat_current_count: 1,
    last_practiced_at: "2026-07-31T01:01:00Z",
  });
});

test("cloze candidates blank exact target phrases in either example", () => {
  const candidates = buildClozeCandidates([
    {
      id: "1",
      word: "galvanic corrosion",
      example_1_en: "Galvanic corrosion can damage the joint.",
      example_1_zh: "電偶腐蝕可能損壞接合處。",
      example_2_en: "The coating limits galvanic corrosion.",
      example_2_zh: "塗層可以限制電偶腐蝕。",
    },
  ]);

  assert.deepEqual(
    candidates.map(({ clozeText, hint, answer }) => ({ clozeText, hint, answer })),
    [
      {
        clozeText: "_____ _____ can damage the joint.",
        hint: "電偶腐蝕可能損壞接合處。",
        answer: "galvanic corrosion",
      },
      {
        clozeText: "The coating limits _____ _____.",
        hint: "塗層可以限制電偶腐蝕。",
        answer: "galvanic corrosion",
      },
    ],
  );
});

test("cloze candidates match simple plural form of a phrase final word", () => {
  const candidates = buildClozeCandidates([
    {
      word: "consultant question",
      example_1_en: "The review board answered several consultant questions during the meeting.",
      example_1_zh: "",
    },
  ]);

  assert.equal(candidates.length, 1);
  assert.equal(candidates[0].clozeText, "The review board answered several _____ _____ during the meeting.");
  assert.equal(candidates[0].answer, "consultant questions");
  assert.deepEqual(
    findTargetPhraseMatches("Several consultant questions remained open.", "consultant question"),
    [{ start: 8, end: 28, text: "consultant questions" }],
  );
});

test("cloze candidates show one blank for each word in a phrase", () => {
  const candidates = buildClozeCandidates([
    {
      word: "subject to confirmation",
      example_1_en: "The result is subject to confirmation.",
      example_1_zh: "結果仍待確認。",
    },
  ]);

  assert.equal(candidates.length, 1);
  assert.equal(candidates[0].clozeText, "The result is _____ _____ _____.");
});

test("cloze candidates exclude partial word matches and unusable examples", () => {
  const candidates = buildClozeCandidates([
    {
      word: "bus",
      example_1_en: "The busbar carries current.",
      example_1_zh: "匯流排承載電流。",
      example_2_en: "Inspect the bus before testing.",
      example_2_zh: "測試前檢查匯流排。",
    },
    {
      word: "bonding",
      example_1_en: "Inspect the enclosure.",
      example_1_zh: "檢查外殼。",
    },
  ]);

  assert.equal(candidates.length, 1);
  assert.equal(candidates[0].clozeText, "Inspect the _____ before testing.");
});

test("answers ignore case and outer whitespace but require exact spelling", () => {
  assert.equal(isCorrectClozeAnswer("  Galvanic Corrosion ", "galvanic corrosion"), true);
  assert.equal(isCorrectClozeAnswer("galvanic  corrosion", "galvanic corrosion"), false);
  assert.equal(isCorrectClozeAnswer("galvanic corrosin", "galvanic corrosion"), false);
});

test("tense highlights match complete words instead of substrings", () => {
  assert.deepEqual(
    findLiteralHighlightRanges(
      "This is a system-level Electromagnetic Compatibility (EMC) integration issue.",
      ["is"],
    ),
    [{ start: 5, end: 7 }],
  );
  assert.deepEqual(
    findLiteralHighlightRanges("The consultant should review this issue.", ["should review"]),
    [{ start: 15, end: 28 }],
  );
});

test("pronunciation omits the YouGlish suffix", () => {
  assert.equal(
    sanitizePronunciation(
      "/ɡælˈvænɪk kəˈroʊʒn/ | https://youglish.com/pronounce/galvanic%20corrosion/english",
    ),
    "/ɡælˈvænɪk kəˈroʊʒn/",
  );
  assert.equal(sanitizePronunciation("/ɪmˈpiːdəns/"), "/ɪmˈpiːdəns/");
});
