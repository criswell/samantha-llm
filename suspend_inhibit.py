#!/usr/bin/env python3
"""
Suspend-inhibition guard for long-running Samantha processes.

Unattended LLM batches (subconscious worker, chunk_retry) die when the machine
suspends mid-run: the remote CLI times out server-side while local timers are
frozen (CLOCK_MONOTONIC does not advance during sleep), leaving sessions
partial and status surfaces lying. Root-cause history: the 2026-11-13/14
process-tree stall (ff0c0b0) and the 2026-11-15/16 idle-suspend stalls, where
logind's lid policy suspended the box when an idle DPMS power-off dropped the
external monitor's video link (docked state flipped false with the lid closed).

This module re-executes the current process under `systemd-inhibit
--what=sleep:idle:handle-lid-switch --mode=block` so logind cannot suspend or
act on the lid switch while the process runs. The inhibitor lock is tied to
the process lifetime and releases automatically on exit, crash, or kill.

Linux + systemd only: every other platform is a no-op. Failure to re-exec
(fallback binary missing, exec error) logs a warning and continues
uninhibited; a batch that can be suspended is strictly better than a batch
that never runs.
"""

import os
import shutil
import sys

# What we inhibit: sleep (suspend/hibernate), idle (idle-action suspend),
# and handle-lid-switch (logind's closed-lid policy, which suspends on dock
# state changes even when the lid was closed while docked).
INHIBIT_WHAT = 'sleep:idle:handle-lid-switch'

# Environment guard set by inhibit_exec() so the child does not re-exec
# itself into a loop. Users can also pre-set it to skip wrapping.
INHIBIT_ENV_VAR = 'SAMANTHA_INHIBIT_WRAPPED'


def _systemd_inhibit_path():
    """Return the absolute path to systemd-inhibit, or None if unavailable."""
    return shutil.which('systemd-inhibit')


def should_inhibit(platform_system=None):
    """True when this process should wrap itself in systemd-inhibit.

    Conditions, all required:
    - Linux (the guard is meaningless elsewhere)
    - systemd-inhibit binary exists
    - this process is not already wrapped (env guard)
    """
    import platform
    system = platform_system if platform_system is not None else platform.system()
    if system != 'Linux':
        return False
    if os.environ.get(INHIBIT_ENV_VAR) == '1':
        return False
    return _systemd_inhibit_path() is not None


def inhibit_exec(argv=None, log=None):
    """Re-exec the current process under systemd-inhibit, if appropriate.

    No-op on non-Linux, without systemd-inhibit, or when already wrapped.
    Never raises: on exec failure this logs a warning and returns so the
    caller proceeds uninhibited (the exec'd image replaces the process only
    on success; on failure we are still here and continue normally).

    Args:
        argv: The command to exec. Defaults to sys.argv (re-exec self).
        log: Optional callable(message) for diagnostics; defaults to no-op.
    """
    emit = log if log is not None else (lambda msg: None)

    if not should_inhibit():
        return

    inhibit = _systemd_inhibit_path()
    if argv is None:
        argv = [sys.executable] + list(sys.argv)

    cmd = [
        inhibit,
        f'--what={INHIBIT_WHAT}',
        '--mode=block',
        '--who=samantha-llm',
        '--why=unattended LLM batch must not be suspended mid-run',
    ] + list(argv)

    # Mark before exec so the child (and any further exec) skips wrapping.
    env = dict(os.environ)
    env[INHIBIT_ENV_VAR] = '1'

    emit(f"[INHIBIT] Re-execing under systemd-inhibit ({INHIBIT_WHAT}, block mode)")
    # Flush userspace buffers: os.exec* replaces the image without flushing
    # Python-level buffers, so anything buffered (e.g. piped stdout) is lost.
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except (AttributeError, ValueError):
        pass
    try:
        os.execvpe(cmd[0], cmd, env)
    except OSError as e:
        # exec failed; we are still the original process. Continue unwrapped.
        emit(f"[INHIBIT] WARN: systemd-inhibit re-exec failed ({e}); "
             f"continuing WITHOUT suspend protection")


if __name__ == '__main__':
    # Wrapped-probe: print marker and exit. Used by --selftest to prove the
    # re-exec actually happened under systemd-inhibit.
    if '--wrapped-probe' in sys.argv:
        print(f"WRAPPED probe: {INHIBIT_ENV_VAR}={os.environ.get(INHIBIT_ENV_VAR)}")
        sys.exit(0)
    # Manual smoke test: python3 suspend_inhibit.py --selftest
    # Should print platform info, then re-exec into the wrapped probe.
    if '--selftest' in sys.argv:
        import platform
        print(f"platform: {platform.system()}")
        print(f"inhibit binary: {_systemd_inhibit_path()}")
        print(f"should_inhibit: {should_inhibit()}")
        if should_inhibit():
            inhibit_exec([sys.executable, __file__, '--wrapped-probe'])
        sys.exit(0)
    print(__doc__)
