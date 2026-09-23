import test from "node:test";
import assert from "node:assert/strict";
import { downloadFile, downloadsPending, subscribeDownloads } from "../src/utils/downloadFile.js";

function browser({ submitError = false } = {}) {
  const events = [];
  const children = [];
  let messageHandler;
  const location = { href: "http://frontend.local/assets", pathname: "/assets" };
  globalThis.window = {
    location,
    addEventListener(type, handler) { if (type === "message") messageHandler = handler; },
  };
  globalThis.document = {
    body: {
      appendChild(element) { children.push(element); events.push(["append", element.tag]); },
    },
    createElement(tag) {
      return {
        tag,
        children: [],
        contentWindow: tag === "iframe" ? {} : undefined,
        appendChild(child) { this.children.push(child); },
        setAttribute() {},
        submit() {
          events.push(["submit", this.method, this.action, this.target, Object.fromEntries(this.children.map((item) => [item.name, item.value]))]);
          if (submitError) throw Error("submit failed");
        },
        remove() { events.push(["remove", tag]); },
      };
    },
  };
  return {
    children,
    events,
    location,
    sendMessage(data, origin = "http://api.local") {
      const frame = children.find((item) => item.tag === "iframe");
      messageHandler({ data, origin, source: frame?.contentWindow });
    },
  };
}

test("uses a hidden iframe, keeps the page, deduplicates preparation, and posts credentials only in the body", async () => {
  const { children, events, location } = browser();
  let resolve;
  let prepares = 0;
  const changes = [];
  const unsubscribe = subscribeDownloads(() => changes.push(downloadsPending()));
  const first = downloadFile("zip", () => { prepares++; return new Promise((done) => { resolve = done; }); }, "http://api.local/downloads/transfer");
  assert.equal(downloadsPending(), true);
  await downloadFile("zip", () => { prepares++; }, "unused");
  assert.equal(prepares, 1);
  resolve({ ticket: "private-ticket", download_id: "abc123" });
  await first;
  assert.equal(typeof window.open, "undefined");
  assert.equal(location.href, "http://frontend.local/assets");
  const frame = children.find((item) => item.tag === "iframe");
  assert.equal(frame.hidden, true);
  const submission = events.find((event) => event[0] === "submit");
  assert.equal(submission[2], "http://api.local/downloads/transfer");
  assert.equal(submission[3], frame.name);
  assert.deepEqual(submission[4], { ticket: "private-ticket", download_id: "abc123" });
  assert.ok(!submission[2].includes("private-ticket"));
  assert.deepEqual(changes, [true, false]);
  unsubscribe();
});

test("preparation failures never navigate and always allow a retry", async () => {
  for (const reason of ["network", "401", "403", "404", "500"]) {
    const { events, location } = browser();
    await assert.rejects(downloadFile("file", async () => { throw Error(reason); }, "/transfer"), new RegExp(reason));
    assert.equal(events.some((event) => event[0] === "submit"), false);
    assert.equal(location.href, "http://frontend.local/assets");
    assert.equal(downloadsPending(), false);
  }
});

test("transfer errors are reported only for the matching hidden frame and origin", async () => {
  const page = browser();
  const errors = [];
  await downloadFile("file", async () => ({ ticket: "ticket", download_id: "id-1" }), "http://api.local/downloads/transfer", {
    onTransferError: (message) => errors.push(message),
  });
  page.sendMessage({ type: "asset-manager-download-error", downloadId: "id-1", message: "거부됨" }, "http://attacker.local");
  assert.deepEqual(errors, []);
  page.sendMessage({ type: "asset-manager-download-error", downloadId: "id-1", message: "거부됨" });
  assert.deepEqual(errors, ["거부됨"]);
  assert.equal(page.events.at(-1)[0], "remove");
});

test("form submission failure removes the frame, form, and lock", async () => {
  const { events } = browser({ submitError: true });
  await assert.rejects(downloadFile("file", async () => ({ ticket: "x", download_id: "id-2" }), "/transfer"), /submit failed/);
  assert.equal(events.filter((event) => event[0] === "remove").length, 2);
  assert.equal(downloadsPending(), false);
});
