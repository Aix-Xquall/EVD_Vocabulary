const assert = require("node:assert/strict");
const test = require("node:test");

const {
  buildSuggestionSegments,
  buildClozeCandidates,
  calculateSpellingSimilarity,
  describePluralAnswerRequirement,
  describeVerbAnswerRequirement,
  findClosestVocabularyMatch,
  findLiteralHighlightRanges,
  findTargetPhraseMatches,
  findVocabularySource,
  incrementPracticeRecord,
  isCorrectClozeAnswer,
  ipaVowelHighlightSegments,
  orderedWordsForPlayback,
  playbackIndex,
  repeatCountForWord,
  resolveChapterWordIndex,
  sanitizePronunciation,
  shouldHidePronunciation,
  vowelHighlightSegments,
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

test("vowel highlighting marks regular English words", () => {
  assert.deepEqual(vowelHighlightSegments("dictate"), [
    { text: "d", isVowel: false },
    { text: "i", isVowel: true },
    { text: "ct", isVowel: false },
    { text: "a", isVowel: true },
    { text: "t", isVowel: false },
    { text: "e", isVowel: true },
  ]);
});

test("vowel highlighting leaves uppercase abbreviations unchanged", () => {
  assert.deepEqual(vowelHighlightSegments("EMC E3 MIL-STD-461 DAQ"), [
    { text: "EMC E3 MIL-STD-461 DAQ", isVowel: false },
  ]);
  const segments = vowelHighlightSegments("Electromagnetic Compatibility (EMC)");
  assert.equal(segments.filter((segment) => segment.isVowel).map((segment) => segment.text).join(""), "Eeoaeioaiii");
  const acronymSegment = segments.find((segment) => segment.text.includes("EMC"));
  assert.equal(acronymSegment.isVowel, false);
});

test("chapter progress follows the saved word after CSV reordering", () => {
  const reorderedWords = [
    { word: "low impedance" },
    { word: "EMC" },
    { word: "bonding" },
  ];
  assert.equal(resolveChapterWordIndex(reorderedWords, "emc", 0), 1);
  assert.equal(resolveChapterWordIndex(reorderedWords, "removed word", 2), 2);
  assert.equal(resolveChapterWordIndex(reorderedWords, "", -1), -1);
});

test("cloze candidates match inflected verbs at the start of a verb phrase", () => {
  const candidates = buildClozeCandidates([
    {
      word: "refer to",
      example_1_en: "This section refers to the applicable EMC requirements.",
      example_1_zh: "本節提到適用的 EMC 要求。",
    },
  ]);

  assert.equal(candidates.length, 1);
  assert.equal(candidates[0].answer, "refers to");
  assert.equal(candidates[0].clozeText, "This section _____ _____ the applicable EMC requirements.");
});

test("cloze candidates match regular past-tense targets", () => {
  const candidates = buildClozeCandidates([
    {
      word: "accumulate",
      example_1_en: "Charge accumulated on the isolated surface.",
      example_1_zh: "電荷累積在隔離表面上。",
    },
  ]);

  assert.equal(candidates.length, 1);
  assert.equal(candidates[0].answer, "accumulated");
});

test("plural answer requirement is explained only for a singular input", () => {
  assert.equal(
    describePluralAnswerRequirement("consultant question", "consultant questions"),
    "因為例句中的目標名詞使用複數型態，所以必須以複數「consultant questions」表示。",
  );
  assert.match(describePluralAnswerRequirement("box", "boxes"), /複數/);
  assert.match(describePluralAnswerRequirement("category", "categories"), /複數/);
  assert.equal(describePluralAnswerRequirement("consultant questions", "consultant questions"), "");
  assert.equal(describePluralAnswerRequirement("consultant answer", "consultant questions"), "");
  assert.equal(describePluralAnswerRequirement("consultant queston", "consultant questions"), "");
});

test("verb answer requirements explain third-person singular and past forms", () => {
  assert.equal(
    describeVerbAnswerRequirement("appear", "appears", {
      name_zh: "現在簡單式",
      formula: "S + V1 / V-s(es)",
      highlights: ["appears"],
    }),
    "因為例句主詞為第三人稱單數，現在簡單式的動詞必須使用第三人稱單數型態「appears」。",
  );
  assert.equal(
    describeVerbAnswerRequirement("accumulate", "accumulated", {
      name_zh: "過去簡單式",
      formula: "S + V-ed",
      highlights: ["accumulated"],
    }),
    "因為例句描述過去發生的動作，所以必須使用過去式「accumulated」。",
  );
  assert.equal(
    describeVerbAnswerRequirement("require", "required", {
      name_zh: "現在簡單式",
      formula: "S + am / is / are + past participle",
      highlights: ["is required"],
    }),
    "因為例句使用被動語態，主要動詞必須使用過去分詞型態「required」。",
  );
});

test("verb explanations do not mistake noun plurals or spelling errors for verbs", () => {
  const tense = {
    name_zh: "過去簡單式",
    formula: "S + V-ed",
    highlights: ["answered"],
  };
  assert.equal(describeVerbAnswerRequirement("consultant question", "consultant questions", tense), "");
  assert.equal(describeVerbAnswerRequirement("accumlate", "accumulated", {
    ...tense,
    highlights: ["accumulated"],
  }), "");
  assert.equal(describePluralAnswerRequirement("appear", "appears", {
    name_zh: "特殊句型/需確認",
    highlights: ["appears"],
  }), "");
});

test("playback indexes follow forward and reverse directions with optional wrapping", () => {
  assert.equal(playbackIndex(1, 4, "forward"), 2);
  assert.equal(playbackIndex(3, 4, "forward"), 3);
  assert.equal(playbackIndex(3, 4, "forward", 1, true), 0);
  assert.equal(playbackIndex(2, 4, "reverse"), 1);
  assert.equal(playbackIndex(0, 4, "reverse"), 0);
  assert.equal(playbackIndex(0, 4, "reverse", 1, true), 3);
  assert.equal(playbackIndex(2, 4, "reverse", -1, true), 3);
});

test("chapter playback reverses a copy without mutating the visible word list", () => {
  const words = [{ word: "first" }, { word: "second" }, { word: "third" }];
  assert.deepEqual(orderedWordsForPlayback(words, "forward"), words);
  assert.deepEqual(orderedWordsForPlayback(words, "reverse"), [...words].reverse());
  assert.deepEqual(words.map((word) => word.word), ["first", "second", "third"]);
});

test("closest vocabulary match reports spelling similarity and meaning source", () => {
  const closest = findClosestVocabularyMatch(
    "dissmilar metal",
    [
      { word: "impedance", chinese_meaning: "阻抗" },
      { word: "dissimilar metal", chinese_meaning: "異種金屬" },
    ],
  );

  assert.equal(closest.word.word, "dissimilar metal");
  assert.equal(closest.word.chinese_meaning, "異種金屬");
  assert.equal(closest.similarity, 94);
  assert.equal(findClosestVocabularyMatch("xyz", [{ word: "impedance" }]), null);
});

test("spelling similarity controls when answer differences are highlighted", () => {
  assert.equal(calculateSpellingSimilarity("dissmilar metal", "dissimilar metal"), 94);
  assert.equal(calculateSpellingSimilarity("box", "boxes"), 60);
  assert.ok(calculateSpellingSimilarity("wrong", "consultant questions") < 60);
});

test("suggestion segments mark only inserted or replaced target characters", () => {
  assert.deepEqual(
    buildSuggestionSegments("dissmilar metal", "dissimilar metal"),
    [
      { text: "diss", changed: false },
      { text: "i", changed: true },
      { text: "milar metal", changed: false },
    ],
  );
  assert.deepEqual(
    buildSuggestionSegments("cot", "cat"),
    [
      { text: "c", changed: false },
      { text: "a", changed: true },
      { text: "t", changed: false },
    ],
  );
});

test("vocabulary source ignores the hard-words copy and reports formal chapter order", () => {
  const target = { word: "dissimilar metal" };
  const source = findVocabularySource(target, [
    { title: "未熟記單字練習", is_hard_words: true, words: [target] },
    {
      title: "MSFC-HDBK-3697",
      words: [{ word: "bonding" }, target],
    },
  ]);

  assert.deepEqual(source, { chapterTitle: "MSFC-HDBK-3697", wordIndex: 2 });
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

test("IPA highlighting marks vowel symbols and their length markers", () => {
  const segments = ipaVowelHighlightSegments("/dɪkˈteɪt iː/");
  assert.equal(segments.map((segment) => segment.text).join(""), "/dɪkˈteɪt iː/");
  assert.equal(
    segments.filter((segment) => segment.isVowel).map((segment) => segment.text).join(""),
    "ɪeɪiː",
  );
});

test("pronunciation is hidden for terms containing Electromagnetic", () => {
  assert.equal(shouldHidePronunciation("external RF Electromagnetic Environment (EME)"), true);
  assert.equal(shouldHidePronunciation("RF transmit mode"), false);
});
