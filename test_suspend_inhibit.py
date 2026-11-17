#!/usr/bin/env python3
"""
Tests for suspend_inhibit: the systemd-inhibit guard for long-running processes.

Platform gating is the contract: Linux + systemd-inhibit present = wrap;
anything else (macOS, Windows, missing binary, already wrapped) = no-op.
The wrapped-probe smoke test exercises the real os.execvpe path on Linux.
"""

import os
import unittest
import unittest.mock

import suspend_inhibit


class ShouldInhibitTests(unittest.TestCase):
    """Gate logic: platform, binary presence, and the env guard."""

    def test_linux_with_binary_wraps(self):
        with unittest.mock.patch.object(suspend_inhibit, '_systemd_inhibit_path',
                                        return_value='/usr/bin/systemd-inhibit'):
            with unittest.mock.patch.dict(os.environ, {}, clear=True):
                self.assertTrue(suspend_inhibit.should_inhibit('Linux'))

    def test_darwin_is_noop(self):
        with unittest.mock.patch.object(suspend_inhibit, '_systemd_inhibit_path',
                                        return_value='/usr/bin/systemd-inhibit'):
            with unittest.mock.patch.dict(os.environ, {}, clear=True):
                self.assertFalse(suspend_inhibit.should_inhibit('Darwin'))

    def test_windows_is_noop(self):
        with unittest.mock.patch.object(suspend_inhibit, '_systemd_inhibit_path',
                                        return_value='/usr/bin/systemd-inhibit'):
            with unittest.mock.patch.dict(os.environ, {}, clear=True):
                self.assertFalse(suspend_inhibit.should_inhibit('Windows'))

    def test_missing_binary_is_noop(self):
        with unittest.mock.patch.object(suspend_inhibit, '_systemd_inhibit_path',
                                        return_value=None):
            with unittest.mock.patch.dict(os.environ, {}, clear=True):
                self.assertFalse(suspend_inhibit.should_inhibit('Linux'))

    def test_env_guard_prevents_recursion(self):
        with unittest.mock.patch.object(suspend_inhibit, '_systemd_inhibit_path',
                                        return_value='/usr/bin/systemd-inhibit'):
            with unittest.mock.patch.dict(os.environ,
                                          {suspend_inhibit.INHIBIT_ENV_VAR: '1'}, clear=True):
                self.assertFalse(suspend_inhibit.should_inhibit('Linux'))


class InhibitExecTests(unittest.TestCase):
    """inhibit_exec: what command gets exec'd, and what happens on failure."""

    def test_builds_expected_command_and_env(self):
        """The exec'd command must carry the full inhibit spec and env guard."""
        captured = {}

        def fake_execvpe(path, args, env):
            captured['path'] = path
            captured['args'] = args
            captured['env'] = env
            # Simulate the real contract: success never returns.
            raise SystemExit(0)

        with unittest.mock.patch.object(suspend_inhibit, 'should_inhibit', return_value=True):
            with unittest.mock.patch.object(os, 'execvpe', fake_execvpe):
                with self.assertRaises(SystemExit):
                    suspend_inhibit.inhibit_exec(
                        argv=['python3', 'worker.py', 't.jsonl', '/cerebrum'],
                        log=lambda m: None,
                    )

        self.assertEqual(captured['path'], '/usr/bin/systemd-inhibit')
        self.assertEqual(
            captured['args'][:4],
            ['/usr/bin/systemd-inhibit',
             f"--what={suspend_inhibit.INHIBIT_WHAT}",
             '--mode=block',
             '--who=samantha-llm'])
        self.assertIn('sleep:idle:handle-lid-switch', suspend_inhibit.INHIBIT_WHAT)
        self.assertEqual(captured['args'][-4:],
                         ['python3', 'worker.py', 't.jsonl', '/cerebrum'])
        self.assertEqual(captured['env'].get(suspend_inhibit.INHIBIT_ENV_VAR), '1')

    def test_exec_failure_continues_uninhibited(self):
        """exec failure must be logged and survived, never raised."""
        events = []

        def failing_execvpe(path, args, env):
            raise OSError(2, 'No such file or directory')

        with unittest.mock.patch.object(suspend_inhibit, 'should_inhibit', return_value=True):
            with unittest.mock.patch.object(os, 'execvpe', failing_execvpe):
                # Must not raise.
                suspend_inhibit.inhibit_exec(argv=['python3', 'x.py'], log=events.append)

        self.assertTrue(any('WARN' in e for e in events), events)
        self.assertTrue(any('WITHOUT suspend protection' in e for e in events), events)

    def test_noop_when_should_inhibit_false(self):
        """Non-Linux / already-wrapped / no binary: no exec, no warning."""
        execed = []
        with unittest.mock.patch.object(suspend_inhibit, 'should_inhibit', return_value=False):
            with unittest.mock.patch.object(os, 'execvpe', lambda *a: execed.append(a)):
                suspend_inhibit.inhibit_exec(argv=['python3', 'x.py'], log=None)
        self.assertEqual(execed, [])


@unittest.skipUnless(suspend_inhibit._systemd_inhibit_path(), 'requires systemd-inhibit')
class WrappedProbeSmokeTest(unittest.TestCase):
    """Real re-exec: the probe runs under an actual systemd-inhibit process."""

    def test_real_reexec_reports_wrapped_env(self):
        import subprocess
        import sys
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'suspend_inhibit.py')
        r = subprocess.run([sys.executable, script, '--selftest'],
                           capture_output=True, text=True, timeout=15)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('WRAPPED probe', r.stdout)
        self.assertIn(f"{suspend_inhibit.INHIBIT_ENV_VAR}=1", r.stdout)
        # Parent-side lines must survive the exec (flush-before-exec contract).
        self.assertIn('platform:', r.stdout)
        self.assertIn('should_inhibit: True', r.stdout)


if __name__ == '__main__':
    unittest.main()
