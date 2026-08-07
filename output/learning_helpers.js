(function exposeLearningHelpers(root, factory) {
  const helpers = factory();
  if (typeof module !== "undefined" && module.exports) {
    module.exports = helpers;
  }
  if (root) {
    root.EvdLearningHelpers = helpers;
  }
}(typeof window !== "undefined" ? window : globalThis, () => {
  function repeatCountForWord(mastered, configuredCount, includeExamples = false) {
    const repeatCount = Math.max(1, Number(configuredCount) || 1);
    return mastered && !includeExamples ? 2 : repeatCount;
  }

  function sanitizePronunciation(value) {
    return String(value || "").split("|", 1)[0].trim();
  }

  function shouldHidePronunciation(word) {
    return /\belectromagnetic\b/i.test(String(word || ""));
  }

  function ipaVowelHighlightSegments(value) {
    const pronunciation = sanitizePronunciation(value);
    const segments = [];
    const ipaVowelPattern = /[iyɨʉɯuɪʏʊeøɘɵɤoəɛœɜɞɚɝʌɔæɐaɶɑɒ]/u;
    let previousWasVowel = false;

    for (const character of pronunciation) {
      const isVowel = ipaVowelPattern.test(character)
        || (previousWasVowel && (character === "ː" || /[\u0300-\u036f]/u.test(character)));
      appendVowelSegment(segments, character, isVowel);
      previousWasVowel = isVowel;
    }
    return segments;
  }

  function vowelHighlightSegments(value) {
    const text = String(value || "");
    const segments = [];
    const tokenPattern = /[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*/g;
    let cursor = 0;
    let match;
    while ((match = tokenPattern.exec(text)) !== null) {
      appendVowelSegment(segments, text.slice(cursor, match.index), false);
      const token = match[0];
      if (isEnglishAcronym(token)) {
        appendVowelSegment(segments, token, false);
      } else {
        Array.from(token).forEach((character) => {
          appendVowelSegment(segments, character, /[aeiou]/i.test(character));
        });
      }
      cursor = match.index + token.length;
    }
    appendVowelSegment(segments, text.slice(cursor), false);
    return segments;
  }

  function isEnglishAcronym(token) {
    const letters = String(token || "").match(/[A-Za-z]/g) || [];
    if (letters.length === 0 || letters.some((letter) => letter !== letter.toUpperCase())) {
      return false;
    }
    return letters.length >= 2 || /\d/.test(token);
  }

  function appendVowelSegment(segments, text, isVowel) {
    if (!text) {
      return;
    }
    const previous = segments[segments.length - 1];
    if (previous && previous.isVowel === isVowel) {
      previous.text += text;
      return;
    }
    segments.push({ text, isVowel });
  }

  function resolveChapterWordIndex(words, savedWordKey, fallbackIndex = -1) {
    const wordList = words || [];
    if (wordList.length === 0) {
      return -1;
    }
    const normalizedWordKey = normalizeClozeAnswer(savedWordKey);
    if (normalizedWordKey) {
      const matchedIndex = wordList.findIndex(
        (word) => normalizeClozeAnswer(word?.word) === normalizedWordKey,
      );
      if (matchedIndex >= 0) {
        return matchedIndex;
      }
    }
    const numericFallback = Number(fallbackIndex);
    if (!Number.isFinite(numericFallback) || numericFallback < 0) {
      return -1;
    }
    return Math.min(Math.floor(numericFallback), wordList.length - 1);
  }

  function incrementPracticeRecord(record, word, isRepeatCycle, practicedAt = new Date().toISOString()) {
    const current = record || {};
    return {
      word: String(word || current.word || "").trim(),
      practice_count: Math.max(0, Number.parseInt(current.practice_count, 10) || 0) + 1,
      repeat_current_count: Math.max(0, Number.parseInt(current.repeat_current_count, 10) || 0)
        + (isRepeatCycle ? 1 : 0),
      last_practiced_at: practicedAt,
    };
  }

  function normalizeClozeAnswer(value) {
    return String(value || "").trim().toLocaleLowerCase("en-US");
  }

  function isCorrectClozeAnswer(answer, expected) {
    return normalizeClozeAnswer(answer) === normalizeClozeAnswer(expected);
  }

  function describePluralAnswerRequirement(input, expected, tense = {}) {
    const inputParts = normalizeClozeAnswer(input).split(/\s+/).filter(Boolean);
    const expectedParts = normalizeClozeAnswer(expected).split(/\s+/).filter(Boolean);
    if (inputParts.length === 0 || inputParts.length !== expectedParts.length) {
      return "";
    }
    const finalIndex = inputParts.length - 1;
    const expectedFinal = expectedParts[finalIndex];
    const isTenseVerb = (tense.highlights || []).some((highlight) => (
      englishTokens(highlight).includes(expectedFinal)
    ));
    if (isTenseVerb) {
      return "";
    }
    const samePrefix = inputParts.slice(0, finalIndex).every(
      (part, index) => part === expectedParts[index],
    );
    if (!samePrefix || !isRegularPluralOf(inputParts[finalIndex], expectedFinal)) {
      return "";
    }
    return `因為例句中的目標名詞使用複數型態，所以必須以複數「${String(expected).trim()}」表示。`;
  }

  function describeVerbAnswerRequirement(input, expected, tense = {}) {
    const inputParts = normalizeClozeAnswer(input).split(/\s+/).filter(Boolean);
    const expectedParts = normalizeClozeAnswer(expected).split(/\s+/).filter(Boolean);
    if (inputParts.length === 0 || inputParts.length !== expectedParts.length) {
      return "";
    }

    const differences = inputParts
      .map((part, index) => ({ input: part, expected: expectedParts[index] }))
      .filter((pair) => pair.input !== pair.expected);
    if (differences.length !== 1) {
      return "";
    }

    const change = differences[0];
    const matchingHighlight = (tense.highlights || []).find((highlight) => (
      englishTokens(highlight).includes(change.expected)
    ));
    if (!matchingHighlight) {
      return "";
    }

    const tenseName = `${tense.display_name_zh || ""} ${tense.name_zh || ""}`;
    const tenseFormula = `${tense.display_formula || ""} ${tense.formula || ""}`;
    const answerText = String(expected).trim();
    if (isThirdPersonSingularOf(change.input, change.expected)
        && (tenseName.includes("現在簡單") || /V-s/i.test(tenseFormula))) {
      return `因為例句主詞為第三人稱單數，現在簡單式的動詞必須使用第三人稱單數型態「${answerText}」。`;
    }

    if (!isPastFormOf(change.input, change.expected)) {
      return "";
    }
    const highlightedTokens = englishTokens(matchingHighlight);
    const verbIndex = highlightedTokens.indexOf(change.expected);
    const auxiliaries = highlightedTokens.slice(0, Math.max(0, verbIndex));
    if (auxiliaries.some((token) => ["am", "is", "are", "was", "were", "be", "been", "being"].includes(token))) {
      return `因為例句使用被動語態，主要動詞必須使用過去分詞型態「${answerText}」。`;
    }
    if (auxiliaries.some((token) => ["have", "has", "had"].includes(token))
        || tenseName.includes("完成") || /p\.p\.|past participle/i.test(tenseFormula)) {
      return `因為例句使用完成式，主要動詞必須使用過去分詞型態「${answerText}」。`;
    }
    if (tenseName.includes("過去簡單") || /V-ed/i.test(tenseFormula)) {
      return `因為例句描述過去發生的動作，所以必須使用過去式「${answerText}」。`;
    }
    return "";
  }

  function isRegularPluralOf(singular, plural) {
    if (!singular || !plural || singular === plural) {
      return false;
    }
    if (/[^aeiou]y$/.test(singular)) {
      return plural === `${singular.slice(0, -1)}ies`;
    }
    if (/[sxz]$/.test(singular) || singular.endsWith("ch") || singular.endsWith("sh")) {
      return plural === `${singular}es`;
    }
    return plural === `${singular}s`;
  }

  function isThirdPersonSingularOf(base, inflected) {
    const irregular = { be: "is", do: "does", have: "has" };
    return irregular[base] === inflected || isRegularPluralOf(base, inflected);
  }

  function isPastFormOf(base, inflected) {
    const irregular = {
      be: ["was", "were"],
      become: ["became"],
      begin: ["began"],
      build: ["built"],
      come: ["came"],
      do: ["did", "done"],
      find: ["found"],
      get: ["got", "gotten"],
      give: ["gave", "given"],
      go: ["went", "gone"],
      have: ["had"],
      keep: ["kept"],
      make: ["made"],
      meet: ["met"],
      read: ["read"],
      run: ["ran", "run"],
      see: ["saw", "seen"],
      send: ["sent"],
      show: ["showed", "shown"],
      take: ["took", "taken"],
      write: ["wrote", "written"],
    };
    if ((irregular[base] || []).includes(inflected)) {
      return true;
    }
    const forms = new Set([`${base}ed`]);
    if (base.endsWith("e")) {
      forms.add(`${base}d`);
    }
    if (/[^aeiou]y$/.test(base)) {
      forms.add(`${base.slice(0, -1)}ied`);
    }
    if (/[aeiou][^aeiouwxy]$/.test(base)) {
      forms.add(`${base}${base.at(-1)}ed`);
    }
    return forms.has(inflected);
  }

  function englishTokens(value) {
    return normalizeClozeAnswer(value).match(/[a-z]+(?:['’][a-z]+)?/g) || [];
  }

  function normalizePlaybackDirection(value) {
    return value === "reverse" ? "reverse" : "forward";
  }

  function playbackIndex(currentIndex, length, direction, offset = 1, wrap = false) {
    if (length <= 0) {
      return -1;
    }
    const normalizedCurrent = Math.min(Math.max(0, Number(currentIndex) || 0), length - 1);
    const directionStep = normalizePlaybackDirection(direction) === "reverse" ? -1 : 1;
    const candidate = normalizedCurrent + directionStep * offset;
    if (candidate >= 0 && candidate < length) {
      return candidate;
    }
    if (!wrap) {
      return normalizedCurrent;
    }
    return candidate < 0 ? length - 1 : 0;
  }

  function orderedWordsForPlayback(words, direction) {
    const ordered = [...(words || [])];
    return normalizePlaybackDirection(direction) === "reverse" ? ordered.reverse() : ordered;
  }

  function findClosestVocabularyMatch(input, words, minimumSimilarity = 60) {
    const normalizedInput = normalizeSimilarityText(input);
    if (!normalizedInput) {
      return null;
    }
    let closest = null;
    (words || []).forEach((word) => {
      const candidate = normalizeSimilarityText(word?.word);
      if (!candidate) {
        return;
      }
      const similarity = similarityPercentage(normalizedInput, candidate);
      if (!closest || similarity > closest.similarity) {
        closest = { word, similarity };
      }
    });
    return closest && closest.similarity >= minimumSimilarity ? closest : null;
  }

  function calculateSpellingSimilarity(first, second) {
    return similarityPercentage(normalizeSimilarityText(first), normalizeSimilarityText(second));
  }

  function buildSuggestionSegments(input, suggestion) {
    const inputChars = Array.from(String(input || "").trim());
    const suggestionChars = Array.from(String(suggestion || "").trim());
    const inputLower = inputChars.map((character) => character.toLocaleLowerCase("en-US"));
    const suggestionLower = suggestionChars.map((character) => character.toLocaleLowerCase("en-US"));
    const distances = Array.from(
      { length: inputChars.length + 1 },
      (_, inputIndex) => Array.from(
        { length: suggestionChars.length + 1 },
        (_, suggestionIndex) => inputIndex === 0 ? suggestionIndex : inputIndex,
      ),
    );

    for (let inputIndex = 1; inputIndex <= inputChars.length; inputIndex += 1) {
      for (let suggestionIndex = 1; suggestionIndex <= suggestionChars.length; suggestionIndex += 1) {
        const substitutionCost = inputLower[inputIndex - 1] === suggestionLower[suggestionIndex - 1] ? 0 : 1;
        distances[inputIndex][suggestionIndex] = Math.min(
          distances[inputIndex - 1][suggestionIndex] + 1,
          distances[inputIndex][suggestionIndex - 1] + 1,
          distances[inputIndex - 1][suggestionIndex - 1] + substitutionCost,
        );
      }
    }

    const characters = [];
    let inputIndex = inputChars.length;
    let suggestionIndex = suggestionChars.length;
    while (inputIndex > 0 || suggestionIndex > 0) {
      const sameCharacter = inputIndex > 0 && suggestionIndex > 0
        && inputLower[inputIndex - 1] === suggestionLower[suggestionIndex - 1];
      if (sameCharacter
          && distances[inputIndex][suggestionIndex] === distances[inputIndex - 1][suggestionIndex - 1]) {
        characters.push({ text: suggestionChars[suggestionIndex - 1], changed: false });
        inputIndex -= 1;
        suggestionIndex -= 1;
      } else if (inputIndex > 0 && suggestionIndex > 0
          && distances[inputIndex][suggestionIndex] === distances[inputIndex - 1][suggestionIndex - 1] + 1) {
        characters.push({ text: suggestionChars[suggestionIndex - 1], changed: true });
        inputIndex -= 1;
        suggestionIndex -= 1;
      } else if (suggestionIndex > 0
          && distances[inputIndex][suggestionIndex] === distances[inputIndex][suggestionIndex - 1] + 1) {
        characters.push({ text: suggestionChars[suggestionIndex - 1], changed: true });
        suggestionIndex -= 1;
      } else {
        inputIndex -= 1;
      }
    }

    return characters.reverse().reduce((segments, character) => {
      const previous = segments[segments.length - 1];
      if (previous && previous.changed === character.changed) {
        previous.text += character.text;
      } else {
        segments.push({ ...character });
      }
      return segments;
    }, []);
  }

  function findVocabularySource(word, chapters) {
    const target = normalizeClozeAnswer(word?.word);
    if (!target) {
      return null;
    }
    for (const chapter of chapters || []) {
      if (chapter?.is_hard_words) {
        continue;
      }
      const wordIndex = (chapter?.words || []).findIndex(
        (candidate) => normalizeClozeAnswer(candidate?.word) === target,
      );
      if (wordIndex >= 0) {
        return {
          chapterTitle: chapter.title || chapter.id || "",
          wordIndex: wordIndex + 1,
        };
      }
    }
    return null;
  }

  function normalizeSimilarityText(value) {
    return normalizeClozeAnswer(value).replace(/\s+/g, " ");
  }

  function similarityPercentage(first, second) {
    const longestLength = Math.max(first.length, second.length);
    if (longestLength === 0) {
      return 100;
    }
    const distance = levenshteinDistance(first, second);
    return Math.max(0, Math.round((1 - distance / longestLength) * 100));
  }

  function levenshteinDistance(first, second) {
    let previous = Array.from({ length: second.length + 1 }, (_, index) => index);
    for (let firstIndex = 1; firstIndex <= first.length; firstIndex += 1) {
      const current = [firstIndex];
      for (let secondIndex = 1; secondIndex <= second.length; secondIndex += 1) {
        const substitutionCost = first[firstIndex - 1] === second[secondIndex - 1] ? 0 : 1;
        current[secondIndex] = Math.min(
          current[secondIndex - 1] + 1,
          previous[secondIndex] + 1,
          previous[secondIndex - 1] + substitutionCost,
        );
      }
      previous = current;
    }
    return previous[second.length];
  }

  function buildClozeCandidates(words) {
    return (words || []).flatMap((word) => {
      const target = String(word?.word || "").trim();
      if (!target) {
        return [];
      }
      return [
        buildClozeCandidate(word, target, 1),
        buildClozeCandidate(word, target, 2),
      ].filter(Boolean);
    });
  }

  function buildClozeCandidate(word, target, exampleIndex) {
    const exampleText = String(word?.[`example_${exampleIndex}_en`] || "");
    const match = findTargetPhraseMatches(exampleText, target)[0];
    if (!match) {
      return null;
    }
    const answer = normalizeClozeAnswer(match.text) === normalizeClozeAnswer(target) ? target : match.text;
    const blank = String(answer).trim().split(/\s+/).map(() => "_____").join(" ");
    return {
      word,
      answer,
      clozeText: `${exampleText.slice(0, match.start)}${blank}${exampleText.slice(match.end)}`,
      hint: String(word?.[`example_${exampleIndex}_zh`] || ""),
      exampleIndex,
    };
  }

  function findTargetPhraseMatches(text, target) {
    const pattern = buildTargetPhrasePattern(target);
    if (!pattern) {
      return [];
    }
    const matches = [];
    let match;
    while ((match = pattern.exec(text)) !== null) {
      const prefix = match[1] || "";
      const start = match.index + prefix.length;
      const end = match.index + match[0].length;
      matches.push({ start, end, text: match[2] });
      if (match.index === pattern.lastIndex) {
        pattern.lastIndex += 1;
      }
    }
    return matches;
  }

  function findLiteralHighlightRanges(text, highlights = []) {
    const value = String(text || "");
    const lowerValue = value.toLocaleLowerCase("en-US");
    const ranges = [];

    highlights.forEach((highlight) => {
      const literal = String(highlight || "").trim();
      if (!literal) {
        return;
      }
      const lowerLiteral = literal.toLocaleLowerCase("en-US");
      let start = 0;
      while ((start = lowerValue.indexOf(lowerLiteral, start)) !== -1) {
        const end = start + literal.length;
        const startsInsideWord = isWordCharacter(literal[0])
          && start > 0
          && isWordCharacter(value[start - 1]);
        const endsInsideWord = isWordCharacter(literal[literal.length - 1])
          && end < value.length
          && isWordCharacter(value[end]);
        if (!startsInsideWord && !endsInsideWord) {
          ranges.push({ start, end });
        }
        start = end || start + 1;
      }
    });
    return ranges;
  }

  function isWordCharacter(value) {
    return /[A-Za-z0-9'’]/.test(String(value || ""));
  }

  function buildTargetPhrasePattern(target) {
    const parts = String(target || "").trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) {
      return null;
    }
    const verbPhraseFollowers = new Set([
      "about", "against", "at", "for", "from", "in", "into", "like", "of", "off", "on", "out", "over", "to", "up", "with",
    ]);
    const phrase = parts.map((part, index) => (
      index === parts.length - 1
        || (index === 0 && parts.length > 1 && verbPhraseFollowers.has(parts[1].toLocaleLowerCase("en-US")))
        ? finalWordVariantPattern(part)
        : escapeRegExp(part)
    )).join("\\s+");
    return new RegExp(`(^|[^A-Za-z0-9])(${phrase})(?=$|[^A-Za-z0-9])`, "gi");
  }

  function finalWordVariantPattern(word) {
    if (!/[A-Za-z]$/.test(word)) {
      return escapeRegExp(word);
    }
    const lower = word.toLocaleLowerCase("en-US");
    if (/[sxz]$/.test(lower) || lower.endsWith("ch") || lower.endsWith("sh")) {
      return `${escapeRegExp(word)}(?:es|ed)?`;
    }
    if (/[^aeiou]y$/.test(lower)) {
      return `${escapeRegExp(word.slice(0, -1))}(?:y|ies|ied)`;
    }
    if (lower.endsWith("e")) {
      return `${escapeRegExp(word)}(?:s|d)?`;
    }
    if (/[aeiou][^aeiouwxy]$/.test(lower)) {
      return `${escapeRegExp(word)}(?:s|ed|${escapeRegExp(word.at(-1))}ed)?`;
    }
    return `${escapeRegExp(word)}(?:s|ed)?`;
  }

  function escapeRegExp(value) {
    return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  return {
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
    normalizeClozeAnswer,
    normalizePlaybackDirection,
    orderedWordsForPlayback,
    playbackIndex,
    repeatCountForWord,
    resolveChapterWordIndex,
    ipaVowelHighlightSegments,
    sanitizePronunciation,
    shouldHidePronunciation,
    vowelHighlightSegments,
  };
}));
