// Drive each dotenv release through its own supported reader API.
// argv: <main.js> <fixture-abs-path> <result-file> <mode: cwd|path>
const fs = require('fs');
const [entry, fixture, resultFile, mode] = process.argv.slice(2);
const grab = () => ({A: process.env.A ?? null, B: process.env.B ?? null, C: process.env.C ?? null});
let out = {mode};
try {
  let m = require(entry);
  if (typeof m === 'function') m = m();           // 0.1.1: module exports a factory
  let result;
  if (mode === 'cwd') {
    result = m.load();
    out.env = grab();
  } else if (typeof m.config === 'function') {
    result = m.config({path: fixture});
    out.env = grab();
  } else if (typeof m.load === 'function') {
    result = m.load({path: fixture});
    out.env = grab();
  } else if (typeof m.parse === 'function') {
    result = m.parse(fs.readFileSync(fixture));
    if (result && typeof result === 'object') {
      out.parsed = {A: result.A ?? null, B: result.B ?? null, C: result.C ?? null};
    }
  } else {
    throw new Error('unsupported reader API');
  }
  // Older APIs return false; newer config returns an error field. A parse result
  // can legitimately contain a string named "error" since it is a map of env values.
  out.failed = result === false || result instanceof Error ||
    (result != null && (out.parsed ? result.error instanceof Error : Boolean(result.error)));
  if (out.failed) out.failure = 'returned';
} catch (e) {
  out.error = String(e && e.message || e);
  out.env = grab();          // partial state, if any assignments happened before the throw
  out.failed = true;
  out.failure = 'thrown';
}
fs.writeFileSync(resultFile, JSON.stringify(out));
