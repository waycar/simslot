# simslot

**Many coding agents, one Mac.** A machine-wide queue for booted iOS
Simulators, so a dozen agents in a dozen git worktrees can run simulator tests
on one Mac without booting a dozen simulators and making every test flaky.

Each booted simulator costs 2–5 GB of memory and about 230 processes. Past
three or four, a laptop starts to swap and UI tests time out for reasons that
have nothing to do with the code. `simslot` caps how many are booted at once
(default 4), grants them first come, first served, leases each one to the
worktree that asked, and takes simulators back from worktrees that are gone or
idle while someone else waits.

It was built for [Waycar](https://waycar.dev)
([source](https://github.com/waycar/waycar-app)), whose iOS app is developed by a
team of AI agents sharing one MacBook, and has run every simulator test there
since September 2026. It is plain Python 3 (standard library only), one
`flock`-guarded JSON state file, and `xcrun simctl`.

## What it does

- **Cap and queue.** `acquire` blocks until a slot is free, FIFO across the
  machine; `--no-wait` exits 75 instead. Several simulators in one request are
  granted all at once or not at all, so an iPhone + iPad run never holds one
  while waiting for the other.
- **Leases.** A grant belongs to the worktree (git top level) that asked.
  Only its owner releases it; `release --all` frees just your own.
- **Reclaim.** A lease whose worktree was deleted is freed. A simulator idle
  for 10 minutes (no process names its UDID) is shut down, but only while
  another worktree is waiting.
- **Pools.** A model name (`iPhone 17 Pro Max`) means any free copy of it
  (`iPhone 17 Pro Max 2`, `… 3`); a UDID or a copy's own name pins one.
  `ensure-pool` creates missing copies of the same device type and runtime.
- **Doctor.** `doctor` says why the queue waits and applies only safe fixes:
  a `simctl diagnose` that has used no CPU for 3 minutes, abandoned leases,
  idle ones while others wait, and an unleased simulator stuck booting or
  failing its health probe twice. It never touches a test that is using CPU.
  Waiters refused for 5 minutes run it themselves.

```sh
udid=$(scripts/sim-slot.py acquire 'iPhone 17 Pro Max')   # waits for a slot
xcodebuild test -destination "id=$udid" ...
scripts/sim-slot.py release --all
scripts/sim-slot.py status                                # holders and queue
scripts/sim-slot.py doctor                                # stuck? start here
```

Two companions come with it:

- `run-app-simulator-tests.py` wraps `xcodebuild test`: it prepares each
  destination simulator (accessibility on, software keyboard not minimized)
  and restores those preferences after, turns off `simctl diagnose` on
  failure, and fails the run on any crash report the app left.
- `check-crash-reports.py` groups the `.ips` crash reports a run left by
  cause; simulated reports (`ExcUserFault_*`) are printed as notes.

## Settings

| Variable | Default | |
| --- | --- | --- |
| `SIMSLOT_SLOTS` | 4 | simulators booted at once, machine-wide |
| `SIMSLOT_IDLE_MINUTES` | 10 | idle time before a lease can be reclaimed |
| `SIMSLOT_DIR` | `~/Library/Application Support/simslot` | queue state |
| `SIMSLOT_RESERVED_PREFIXES` | none | comma-separated name prefixes, matched exactly (`CI ,Bug #`): those simulators are pinned by name, never join a pool, and the doctor never restarts them; a lease on one is reclaimed like any other |
| `SIMSLOT_CI_LOCK_ROOTS` | none | colon-separated folders, besides `/tmp/simslot-ci-locks`, where a CI runner claims a simulator it manages itself (`device-<UDID>/pid` and `start`, the pid's `ps -o lstart=`); claimed ones are left alone |
| `SIMSLOT_CRASH_BUNDLE_PREFIX` | all bundles | crash reports that count, e.g. `com.example.app` (or `--bundle-prefix`) |
| `SIMSLOT_CRASH_IMAGE_PREFIX`, `SIMSLOT_CRASH_TEST_IMAGE_PREFIX` | any image | which frames are the app's and the tests', for grouping crashes |
| `SIMSLOT_CRASH_REPORTS_DIR`, `SIMSLOT_CRASH_REPORT_SETTLE_SECONDS` | `~/Library/Logs/DiagnosticReports`, 3 | where the runner's crash check looks, and how long it waits for ReportCrash |

## Tests

`scripts/test-sim-slot.sh` drives the queue against a fake CoreSimulator, a
fake process table and seeded queue state; it never touches a real simulator
and runs on Linux. `scripts/test-check-crash-reports.py` covers the crash
checker. CI runs both on GitHub's hosted Ubuntu runners.

## License

Apache-2.0. Copyright 2026 OTREVA, LLC. `run-app-simulator-tests.py` started
in [Heeler](https://github.com/ZingerLittleBee/Heeler) (Apache-2.0,
© ZingerLittleBee and Heeler contributors); see [NOTICE](NOTICE).
