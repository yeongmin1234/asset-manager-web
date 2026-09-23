import test from "node:test";
import assert from "node:assert/strict";
import { downloadFile, downloadsPending, subscribeDownloads } from "../src/utils/downloadFile.js";

function browser({ blocked = false, submitError = false } = {}) {
  const events = [];
  const target = { closed: false, document: { body: {} }, close() { this.closed = true; } };
  globalThis.window = { open(url, name) { events.push(["open", url, name]); return blocked ? null : target; } };
  globalThis.document = {
    body: { appendChild() { events.push(["append"]); } },
    createElement(tag) { return { tag, appendChild(input) { this.input = input; },
      submit() { events.push(["submit", this.method, this.action, this.input.value]); if (submitError) throw Error("submit failed"); },
      remove() { events.push(["remove"]); } }; },
  };
  target.document = { ...globalThis.document };
  return { events, target };
}

test("opens during click, deduplicates preparation, posts credentials only in body, always unlocks", async () => {
  const { events, target } = browser();
  let resolve;
  let prepares = 0;
  const changes = [];
  const unsubscribe = subscribeDownloads(() => changes.push(downloadsPending()));
  const first = downloadFile("zip", () => { prepares++; return new Promise((r) => { resolve = r; }); }, "https://api/downloads/transfer");
  assert.equal(events[0][0], "open");
  assert.equal(downloadsPending(), true);
  await downloadFile("zip", () => { prepares++; }, "unused");
  assert.equal(prepares, 1);
  resolve({ ticket: "private-ticket" });
  await first;
  assert.equal(target.opener, null);
  assert.deepEqual(events.find((e) => e[0] === "submit"), ["submit", "POST", "https://api/downloads/transfer", "private-ticket"]);
  assert.equal(events.at(-1)[0], "remove");
  assert.deepEqual(changes, [true, false]);
  unsubscribe();
});

test("network/401/403/404/500 errors close preparation window and allow retries", async () => {
  for (const reason of ["network", "401", "403", "404", "500"]) {
    const { target } = browser();
    await assert.rejects(downloadFile("file", async () => { throw Error(reason); }, "/transfer"), new RegExp(reason));
    assert.equal(target.closed, true);
    assert.equal(downloadsPending(), false);
    browser();
    await downloadFile("file", async () => ({ ticket: "retry" }), "/transfer");
  }
});

test("popup blocking and closed windows produce actionable errors", async () => {
  browser({ blocked: true });
  await assert.rejects(downloadFile("file", async () => { throw Error("should not request"); }, "/transfer"), /차단/);
  const { target } = browser();
  await assert.rejects(downloadFile("file", async () => { target.closed = true; return { ticket: "x" }; }, "/transfer"), /닫혔/);
  assert.equal(downloadsPending(), false);
});

test("form failure cleans DOM and unlocks", async () => {
  const { events } = browser({ submitError: true });
  await assert.rejects(downloadFile("file", async () => ({ ticket: "x" }), "/transfer"), /submit failed/);
  assert.equal(events.at(-1)[0], "remove");
  assert.equal(downloadsPending(), false);
});
