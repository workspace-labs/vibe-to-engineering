// dotenv decode harness (v3): drive a specific release exactly as it exposes itself.
// argv: <main.js> <fixture-abs-path> <result-file> <mode: cwd|path>
// v3: on exception, still capture the (possibly partial) environment state and mark the
// observation as failed — a crash must never be silently equated with "no readings".
const fs = require('fs');
const [entry, fixture, resultFile, mode] = process.argv.slice(2);
const grab = () => ({A: process.env.A ?? null, B: process.env.B ?? null, C: process.env.C ?? null});
let out = {mode};
try {
  let m = require(entry);
  if (typeof m === 'function') m = m();           // 0.1.1: module exports a factory
  if (mode === 'cwd') {
    m.load();
    out.env = grab();
  } else if (typeof m.config === 'function') {
    m.config({path: fixture});
    out.env = grab();
  } else if (typeof m.load === 'function') {
    m.load({path: fixture});
    out.env = grab();
  } else if (typeof m.parse === 'function') {
    const r = m.parse(fs.readFileSync(fixture));
    out.parsed = {A: r.A ?? null, B: r.B ?? null, C: r.C ?? null};
  } else {
    out.keys = Object.keys(m);
  }
  out.failed = false;
} catch (e) {
  out.error = String(e && e.message || e);
  out.env = grab();          // partial state, if any assignments happened before the throw
  out.failed = true;
}
fs.writeFileSync(resultFile, JSON.stringify(out));
