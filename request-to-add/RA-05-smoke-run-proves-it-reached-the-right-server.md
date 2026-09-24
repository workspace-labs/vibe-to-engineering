# RA-05 — a server smoke run proves it is talking to the server it started

## What is missing

For a web server or API, the smoke run is: `start it, call the main routes, compare status codes and key content, stop it` (`migration-plan.md:49`). Nothing says to use a free port, to check that the process it started is the one answering, or to fail when the server didn't start. Another program already on the port, or a server left running from an earlier check, silently answers instead.

The dangerous case: a phase breaks the server so it fails to start, while an old copy from the baseline is still listening on the same port. The "after" check then tests **the old code** and passes.

## How it showed up

On the test PC (2026-09-24), ports **8001** and **8010** were already used by unrelated services. Starting a second copy of spendly on 8001 failed (`OSError: [Errno 98] Address already in use`, in the server's log only). Calls to `localhost:8001` still got answers, from the other service:

```
8001 /                            303
8001 /api/summary?month=2026-08   404
8001 /export.csv                  404
```

The same happened on 8010. Only reading the server's log showed that the app never started. A smoke check that looks only at responses would have reported a failure with the wrong cause. If the answers had matched (a stale spendly still running), it would have reported a pass.

## Where

- `references/migration-plan.md:49` → `  - web server or API: start it, call the main routes, compare status codes and key content, stop it;`
- `references/migration-plan.md:54` → `  Stop anything the smoke run starts.`

## Added means

`migration-plan.md` section 3 says, for any check that starts a server or other long-running process:

1. **Free port:** ask the system for a free port (bind to port 0) and pass it in. Never assume the default or a fixed port is free. If the app can't take a port, check that the port is free before starting.
2. **Started and alive:** the check keeps the process handle, waits for the app's own start-up signal (a log line, or a health route), and fails at once if the process exits. It checks before *and after* the calls that its own process is still running and is the one listening on the port.
3. **Nothing stale:** before starting, confirm no earlier check's process is still running. After the calls, stop the process and confirm it's gone.
4. The check records the port, the process id and the start-up log in `evidence/`.
5. A test in `test_protocol.py` checks that the rule is in the reference.

## Ideas (not tried)

- The safety-net smoke script written in Phase 1 can do all of this in about 20 lines of Python standard library: `socket` to find the port, `subprocess.Popen`, poll until the port answers, and `proc.poll()` checks before and after.
