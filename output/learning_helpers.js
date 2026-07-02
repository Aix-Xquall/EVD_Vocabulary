(function exposeLearningHelpers(root, factory) {
  const helpers = factory();
  if (typeof module !== "undefined" && module.exports) {
    module.exports = helpers;
  }
  if (root) {
    root.EvdLearningHelpers = helpers;
  }
}(typeof window !== "undefined" ? window : globalThis, () => {
  function repeatCountForWord(mastered, configuredCount) {
    return mastered ? 2 : Math.max(1, Number(configuredCount) || 1);
  }

  function sanitizePronunciation(value) {
    return String(value || "").split("|", 1)[0].trim();
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
    const clozeText = replaceExactPhrase(exampleText, target);
    if (!clozeText) {
      return null;
    }
    return {
      word,
      answer: target,
      clozeText,
      hint: String(word?.[`example_${exampleIndex}_zh`] || ""),
      exampleIndex,
    };
  }

  function replaceExactPhrase(text, target) {
    const escapedTarget = target.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const pattern = new RegExp(`(^|[^A-Za-z0-9])(${escapedTarget})(?=$|[^A-Za-z0-9])`, "gi");
    if (!pattern.test(text)) {
      return "";
    }
    pattern.lastIndex = 0;
    return text.replace(pattern, (match, prefix) => `${prefix}_____`);
  }

  return {
    buildClozeCandidates,
    isCorrectClozeAnswer,
    normalizeClozeAnswer,
    repeatCountForWord,
    sanitizePronunciation,
  };
}));
