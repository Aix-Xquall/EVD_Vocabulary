const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const script = fs.readFileSync(
  path.join(__dirname, "../apps_script/hard_words_web_app.gs"),
  "utf8",
);

function merge(existing, incoming) {
  const headers = ["word", "note"];
  const sheet = {
    getLastRow: () => 2,
    getRange: (row, column) => ({
      getValues: () => [["__EVD_PRACTICE_STATS__"]],
      getValue: () => JSON.stringify(existing),
    }),
  };
  const context = vm.createContext({ sheet, headers, incoming });
  vm.runInContext(script, context);
  return JSON.parse(vm.runInContext(
    "mergePracticeStateNote(sheet, headers, JSON.stringify(incoming))",
    context,
  ));
}

test("familiar MSFC keys survive an older device settings write", () => {
  const existing = {
    r: [],
    su: "2026-10-19T10:00:00Z",
    s: { playback_rate: 1.2, familiar_msfc_word_keys: ["gasket"] },
  };
  const incoming = {
    r: [],
    su: "2026-10-19T09:00:00Z",
    s: { playback_rate: 0.8, familiar_msfc_word_keys: ["Piano Hinge"] },
  };
  const result = merge(existing, incoming);
  assert.equal(result.s.playback_rate, 1.2);
  assert.deepEqual(result.s.familiar_msfc_word_keys, ["gasket", "piano hinge"]);
  assert.ok(result.su > existing.su);
});
