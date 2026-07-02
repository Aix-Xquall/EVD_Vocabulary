const assert = require("node:assert/strict");
const test = require("node:test");

const {
  buildClozeCandidates,
  isCorrectClozeAnswer,
  repeatCountForWord,
  sanitizePronunciation,
} = require("../web/learning_helpers.js");

test("mastered words use two English repetitions", () => {
  assert.equal(repeatCountForWord(true, 5), 2);
  assert.equal(repeatCountForWord(false, 5), 5);
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
        clozeText: "_____ can damage the joint.",
        hint: "電偶腐蝕可能損壞接合處。",
        answer: "galvanic corrosion",
      },
      {
        clozeText: "The coating limits _____.",
        hint: "塗層可以限制電偶腐蝕。",
        answer: "galvanic corrosion",
      },
    ],
  );
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

test("pronunciation omits the YouGlish suffix", () => {
  assert.equal(
    sanitizePronunciation(
      "/ɡælˈvænɪk kəˈroʊʒn/ | https://youglish.com/pronounce/galvanic%20corrosion/english",
    ),
    "/ɡælˈvænɪk kəˈroʊʒn/",
  );
  assert.equal(sanitizePronunciation("/ɪmˈpiːdəns/"), "/ɪmˈpiːdəns/");
});
