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

  function describePluralAnswerRequirement(input, expected) {
    const inputParts = normalizeClozeAnswer(input).split(/\s+/).filter(Boolean);
    const expectedParts = normalizeClozeAnswer(expected).split(/\s+/).filter(Boolean);
    if (inputParts.length === 0 || inputParts.length !== expectedParts.length) {
      return "";
    }
    const finalIndex = inputParts.length - 1;
    const samePrefix = inputParts.slice(0, finalIndex).every(
      (part, index) => part === expectedParts[index],
    );
    if (!samePrefix || !isRegularPluralOf(inputParts[finalIndex], expectedParts[finalIndex])) {
      return "";
    }
    return `因為例句中的目標名詞使用複數型態，所以必須以複數「${String(expected).trim()}」表示。`;
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
    const phrase = parts.map((part, index) => (
      index === parts.length - 1 ? finalWordVariantPattern(part) : escapeRegExp(part)
    )).join("\\s+");
    return new RegExp(`(^|[^A-Za-z0-9])(${phrase})(?=$|[^A-Za-z0-9])`, "gi");
  }

  function finalWordVariantPattern(word) {
    if (!/[A-Za-z]$/.test(word)) {
      return escapeRegExp(word);
    }
    const lower = word.toLocaleLowerCase("en-US");
    if (/[sxz]$/.test(lower) || lower.endsWith("ch") || lower.endsWith("sh")) {
      return `${escapeRegExp(word)}(?:es)?`;
    }
    if (/[^aeiou]y$/.test(lower)) {
      return `${escapeRegExp(word.slice(0, -1))}(?:y|ies)`;
    }
    return `${escapeRegExp(word)}s?`;
  }

  function escapeRegExp(value) {
    return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  return {
    buildSuggestionSegments,
    buildClozeCandidates,
    describePluralAnswerRequirement,
    findClosestVocabularyMatch,
    findLiteralHighlightRanges,
    findTargetPhraseMatches,
    findVocabularySource,
    incrementPracticeRecord,
    isCorrectClozeAnswer,
    normalizeClozeAnswer,
    repeatCountForWord,
    sanitizePronunciation,
  };
}));
