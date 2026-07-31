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
    return {
      word,
      answer: normalizeClozeAnswer(match.text) === normalizeClozeAnswer(target) ? target : match.text,
      clozeText: `${exampleText.slice(0, match.start)}_____${exampleText.slice(match.end)}`,
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
    buildClozeCandidates,
    findLiteralHighlightRanges,
    findTargetPhraseMatches,
    incrementPracticeRecord,
    isCorrectClozeAnswer,
    normalizeClozeAnswer,
    repeatCountForWord,
    sanitizePronunciation,
  };
}));
