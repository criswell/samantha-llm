#!/usr/bin/env python3
"""Tests for write_config unmanaged-key preservation.

Regression tests for the 2026-11-12 config-loss incident: an opencode
process started before the user added the `subconscious` section to
config.json later auto-linked a workspace and rewrote the file from its
stale in-memory dict, silently dropping the subconscious keys (which
took the abacus analyzer config down with it).

Hermetic: SAMANTHA_CONFIG_HOME is pointed at a temp dir; the real user
config is never read or written.
"""

import json
import os
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def load_cli():
    loader = SourceFileLoader('samantha_llm_cli', str(Path(__file__).parent / 'samantha-llm'))
    spec = spec_from_loader(loader.name, loader)
    module = module_from_spec(spec)
    loader.exec_module(module)
    return module


class WriteConfigPreservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cli = load_cli()
        # Point the config dir at the temp dir before any call
        self._orig_home = os.environ.get('HOME')
        os.environ['HOME'] = self.tmp.name
        self.config_file = Path(self.tmp.name) / '.config' / 'samantha-llm' / 'config.json'
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self._orig_home is None:
            os.environ.pop('HOME', None)
        else:
            os.environ['HOME'] = self._orig_home
        self.tmp.cleanup()

    def write_disk(self, payload):
        self.config_file.write_text(json.dumps(payload, indent=2))

    def read_disk(self):
        return json.loads(self.config_file.read_text())

    def test_unmanaged_key_preserved_when_absent_from_memory(self):
        """The incident: on-disk has subconscious, in-memory dict does not."""
        self.write_disk({
            'version': '0.5.0',
            'agents': {'abacus': {'command': 'abacusai'}},
            'subconscious': {'analyzer_agent': 'abacus'},
        })
        stale = {
            'version': '0.5.0',
            'agents': {'abacus': {'command': 'abacusai'}},
            'workspaces': {'/home/sam/work': {'manual': False}},
        }
        self.assertTrue(self.cli.write_config(stale))
        merged = self.read_disk()
        self.assertEqual(
            merged['subconscious'], {'analyzer_agent': 'abacus'},
            'unmanaged on-disk key must survive a write from stale state'
        )
        self.assertEqual(
            merged['workspaces'], stale['workspaces'],
            'managed keys keep the in-memory values'
        )

    def test_unmanaged_key_on_disk_wins_only_when_missing_in_memory(self):
        """If the caller DOES have the key in memory, in-memory wins."""
        self.write_disk({
            'version': '0.5.0',
            'subconscious': {'analyzer_agent': 'old-value'},
        })
        newer = {
            'version': '0.5.0',
            'subconscious': {'analyzer_agent': 'new-value'},
        }
        self.assertTrue(self.cli.write_config(newer))
        self.assertEqual(self.read_disk()['subconscious']['analyzer_agent'], 'new-value')

    def test_unmanaged_key_removal_requires_file_surgery(self):
        """Documented semantics: absent-from-caller means stale, not deleting.

        A caller that omits an unmanaged key gets it preserved (that is the
        incident fix). Dropping an unmanaged key from disk is explicit file
        surgery, not a write_config call.
        """
        self.write_disk({
            'version': '0.5.0',
            'subconscious': {'analyzer_agent': 'abacus'},
        })
        removal = {'version': '0.5.0'}
        self.assertTrue(self.cli.write_config(removal))
        self.assertIn(
            'subconscious', self.read_disk(),
            'absent-from-caller is stale-process semantics, key preserved'
        )

    def test_multiple_unmanaged_keys_preserved(self):
        self.write_disk({
            'version': '0.5.0',
            'subconscious': {'analyzer_agent': 'abacus'},
            'custom_thing': {'nested': [1, 2, 3]},
        })
        self.assertTrue(self.cli.write_config({'version': '0.5.0'}))
        merged = self.read_disk()
        self.assertEqual(merged['custom_thing'], {'nested': [1, 2, 3]})
        self.assertEqual(merged['subconscious'], {'analyzer_agent': 'abacus'})

    def test_missing_file_writes_fresh(self):
        self.assertTrue(self.cli.write_config({'version': '0.5.0'}))
        self.assertEqual(self.read_disk(), {'version': '0.5.0'})

    def test_no_tmp_file_left_behind(self):
        self.assertTrue(self.cli.write_config({'version': '0.5.0'}))
        leftovers = list(self.config_file.parent.glob('*.tmp'))
        self.assertEqual(leftovers, [], 'atomic write must not leave temp files')


if __name__ == '__main__':
    unittest.main(verbosity=2)
