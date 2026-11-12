#!/usr/bin/env python3
"""
Tests for OpenAI Codex support.
"""

import copy
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.machinery
import importlib.util

import analyzer_factory
from codex_analyzer import CodexAnalyzer


def load_cli_module():
    """Load the extensionless samantha-llm script as a module."""
    script_path = Path(__file__).parent / 'samantha-llm'
    loader = importlib.machinery.SourceFileLoader('samantha_llm_cli_for_test', str(script_path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class FakeAnalyzerModule:
    """Minimal analyzer module stand-in for factory tests."""

    def __init__(self, name):
        self.name = name

    def create_analyzer(self, prompt_path, output_dir=None):
        return {
            'name': self.name,
            'prompt_path': prompt_path,
            'output_dir': output_dir,
        }


class TestCodexSetup(unittest.TestCase):
    """Tests for Codex CLI setup integration."""

    def test_interactive_setup_adds_codex_agent(self):
        cli = load_cli_module()
        config = {
            'version': '0.5.0',
            'repo_path': '/tmp/samantha-llm',
            'agents': {},
            'workspaces': {},
        }
        written = []

        def write_config(updated, changes=None):
            written.append(copy.deepcopy(changes if changes is not None else updated))
            return True

        with patch.object(cli, 'read_config', return_value=config), \
             patch.object(cli, 'write_config', side_effect=write_config), \
             patch('builtins.input', side_effect=['4']):
            result = cli.cmd_setup(SimpleNamespace(default_agent=None))

        self.assertEqual(result, 0)
        saved = written[-1]
        self.assertEqual(saved['set']['default_agent'], 'codex')
        self.assertEqual(saved['set']['agents']['codex']['command'], 'codex --no-alt-screen')
        self.assertEqual(saved['set']['agents']['codex']['bootstrap_file'], 'BOOTSTRAP_PROMPT.md')

    def test_interactive_setup_adds_abacus_agent_using_installed_cli(self):
        cli = load_cli_module()
        config = {
            'version': '0.5.0',
            'repo_path': '/tmp/samantha-llm',
            'agents': {},
            'workspaces': {},
        }
        written = []

        def write_config(updated, changes=None):
            written.append(copy.deepcopy(changes if changes is not None else updated))
            return True

        with patch.object(cli, 'read_config', return_value=config), \
             patch.object(cli, 'write_config', side_effect=write_config), \
             patch('builtins.input', side_effect=['2']):
            result = cli.cmd_setup(SimpleNamespace(default_agent=None))

        self.assertEqual(result, 0)
        self.assertEqual(written[-1]['set']['default_agent'], 'abacus')
        self.assertEqual(written[-1]['set']['agents']['abacus']['command'], 'abacusai')

    def test_interactive_setup_adds_qwen3_agent(self):
        cli = load_cli_module()
        config = {
            'version': '0.5.0',
            'repo_path': '/tmp/samantha-llm',
            'agents': {},
            'workspaces': {},
        }
        written = []

        def write_config(updated, changes=None):
            written.append(copy.deepcopy(changes if changes is not None else updated))
            return True

        with patch.object(cli, 'read_config', return_value=config), \
             patch.object(cli, 'write_config', side_effect=write_config), \
             patch('builtins.input', side_effect=['5']):
            result = cli.cmd_setup(SimpleNamespace(default_agent=None))

        self.assertEqual(result, 0)
        saved = written[-1]
        self.assertEqual(saved['set']['default_agent'], 'qwen3')
        self.assertEqual(
            saved['set']['agents']['qwen3']['command'],
            'ollama launch qwen --model qwen3-coder:480b-cloud -- --bare'
        )
        self.assertEqual(saved['set']['agents']['qwen3']['bootstrap_file'], 'BOOTSTRAP_PROMPT.md')
        self.assertEqual(saved['set']['agents']['qwen3']['bootstrap_input'], 'qwen_system')

    def test_bootstrap_input_defaults_to_argument_mode(self):
        cli = load_cli_module()

        self.assertEqual(
            cli.get_bootstrap_input_mode({'command': 'claude'}),
            'argument'
        )

    def test_legacy_abacus_npx_command_uses_installed_cli(self):
        cli = load_cli_module()

        with patch.object(cli.shutil, 'which', return_value='C:/tools/abacusai.CMD'):
            self.assertEqual(
                cli.resolve_agent_command('abacus', 'npx abacusai'),
                'abacusai'
            )

    def test_legacy_abacus_npx_command_is_preserved_without_installed_cli(self):
        cli = load_cli_module()

        with patch.object(cli.shutil, 'which', return_value=None):
            self.assertEqual(
                cli.resolve_agent_command('abacus', 'npx abacusai'),
                'npx abacusai'
            )

    def test_other_agent_commands_are_not_rewritten(self):
        cli = load_cli_module()

        with patch.object(cli.shutil, 'which', return_value='C:/tools/abacusai.CMD'):
            self.assertEqual(
                cli.resolve_agent_command('custom', 'npx abacusai'),
                'npx abacusai'
            )

    def test_refresh_updates_launcher_from_configured_repo_without_writing_config(self):
        cli = load_cli_module()
        config = {
            'repo_path': 'C:/work/samantha-llm',
            'default_agent': 'abacus',
            'agents': {'abacus': {'command': 'abacusai'}},
            'personas': {'samantha-hartwell': {'type': 'builtin'}},
            'workspaces': {'C:/work/app': {'manual': True}},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_dir = Path(temp_dir)
            (repo_dir / 'samantha-llm').write_text('launcher', encoding='utf-8')
            config['repo_path'] = str(repo_dir)
            original_config = copy.deepcopy(config)

            with patch.object(cli, 'read_config', return_value=config), \
                 patch.object(cli, 'is_installed', return_value=True), \
                 patch.object(cli, 'get_platform', return_value='windows'), \
                 patch.object(cli, 'install_windows') as install_windows, \
                 patch.object(cli, 'get_install_path', return_value=Path('C:/install/samantha-llm.bat')):
                result = cli.cmd_refresh(SimpleNamespace())

        self.assertEqual(result, 0)
        install_windows.assert_called_once_with(repo_dir=repo_dir, configure_path=False)
        self.assertEqual(config, original_config)

    def test_windows_refresh_copies_launcher_without_modifying_path(self):
        cli = load_cli_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo_dir = root / 'repo'
            install_dir = root / 'install'
            repo_dir.mkdir()
            (repo_dir / 'samantha-llm').write_text('updated launcher', encoding='utf-8')
            install_dir.mkdir()
            wrapper = install_dir / 'samantha-llm.bat'

            with patch.object(cli, 'get_install_dir', return_value=install_dir), \
                 patch.object(cli, 'get_install_path', return_value=wrapper), \
                 patch.object(cli, 'check_path') as check_path, \
                 patch.object(cli, 'add_to_windows_path') as add_to_path:
                cli.install_windows(repo_dir=repo_dir, configure_path=False)

            installed_script = (install_dir / 'samantha-llm').read_text(encoding='utf-8')
            self.assertEqual(installed_script, 'updated launcher')
            self.assertIn('python', wrapper.read_text(encoding='utf-8'))
            check_path.assert_not_called()
            add_to_path.assert_not_called()

    def test_refresh_fails_when_configured_repo_has_no_launcher(self):
        cli = load_cli_module()
        config = {'repo_path': 'C:/missing/repo'}

        with patch.object(cli, 'read_config', return_value=config), \
             patch.object(cli, 'is_installed', return_value=True), \
             patch.object(cli, 'install_windows') as install_windows:
            result = cli.cmd_refresh(SimpleNamespace())

        self.assertEqual(result, 1)
        install_windows.assert_not_called()

    def test_setup_default_accepts_codex(self):
        cli = load_cli_module()
        config = {
            'version': '0.5.0',
            'repo_path': '/tmp/samantha-llm',
            'default_agent': 'claude',
            'agents': {
                'codex': {
                    'command': 'codex --no-alt-screen',
                    'bootstrap_file': 'BOOTSTRAP_PROMPT.md',
                }
            },
            'workspaces': {},
        }
        written = []

        def write_config(updated, changes=None):
            written.append(copy.deepcopy(changes if changes is not None else updated))
            return True

        with patch.object(cli, 'read_config', return_value=config), \
             patch.object(cli, 'write_config', side_effect=write_config):
            result = cli.cmd_setup(SimpleNamespace(default_agent='codex'))

        self.assertEqual(result, 0)
        self.assertEqual(written[-1]['set']['default_agent'], 'codex')

    def test_abacus_windows_command_passes_bootstrap_as_initial_message(self):
        cli = load_cli_module()

        command = cli.build_bootstrap_shell_command(
            'abacusai',
            r'C:\Users\Owner\AppData\Local\Temp\bootstrap prompt.md',
            'windows',
            'argument'
        )

        self.assertEqual(
            command,
            "& abacusai (Get-Content -Raw 'C:\\Users\\Owner\\AppData\\Local\\Temp\\bootstrap prompt.md')"
        )

    def test_qwen3_prompt_interactive_command_receives_bootstrap_argument(self):
        cli = load_cli_module()

        command = cli.build_argument_bootstrap_shell_command(
            'ollama launch qwen --model qwen3-coder:480b-cloud -- --prompt-interactive',
            '/tmp/bootstrap prompt.md',
            'linux'
        )

        self.assertIn('ollama launch qwen --model qwen3-coder:480b-cloud -- --prompt-interactive', command)
        self.assertIn('"$(cat \'/tmp/bootstrap prompt.md\')"', command)
        self.assertNotIn('script -q', command)

    def test_qwen3_system_prompt_command_appends_bootstrap_to_system_prompt(self):
        cli = load_cli_module()

        command = cli.build_bootstrap_shell_command(
            'ollama launch qwen --model qwen3-coder:480b-cloud -- --bare',
            '/tmp/bootstrap prompt.md',
            'linux',
            'qwen_system'
        )

        self.assertIn('ollama launch qwen --model qwen3-coder:480b-cloud -- --bare', command)
        self.assertIn('--append-system-prompt "$(cat \'/tmp/bootstrap prompt.md\')"', command)
        self.assertIn('--prompt-interactive', command)
        self.assertIn('Begin the Samantha Hartwell bootstrap now.', command)
        self.assertNotIn('script -q', command)


class TestCodexAnalyzer(unittest.TestCase):
    """Tests for Codex analyzer command execution and parsing."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)
        self.prompt_path = self.root / 'prompt.txt'
        self.recording_path = self.root / 'parsed_20260527_120000.txt'
        self.output_dir = self.root / 'analyses'
        self.prompt_path.write_text('Analyze this conversation.')
        self.recording_path.write_text('User: hello\nAssistant: hi')

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_analyze_invokes_codex_exec_and_parses_schema_output(self):
        final_output = {
            'patterns': ['Uses Codex'],
            'decisions': ['Added Codex support'],
            'todos': ['Run tests'],
            'preferences': ['Keep provider behavior explicit'],
            'learnings': ['Codex exec can write final JSON'],
            'summary': 'Codex support was analyzed.',
        }
        captured = {}

        def fake_run(cmd, input, capture_output, text, timeout):
            captured['cmd'] = cmd
            captured['input'] = input
            captured['capture_output'] = capture_output
            captured['text'] = text
            captured['timeout'] = timeout
            output_path = Path(cmd[cmd.index('--output-last-message') + 1])
            output_path.write_text(json.dumps(final_output))
            return subprocess.CompletedProcess(cmd, 0, stdout='', stderr='')

        analyzer = CodexAnalyzer(self.prompt_path, output_dir=self.output_dir)
        with patch('codex_analyzer.subprocess.run', side_effect=fake_run):
            result = analyzer.analyze(self.recording_path)

        self.assertEqual(captured['cmd'][:4], ['codex', '--ask-for-approval', 'never', 'exec'])
        self.assertIn('--sandbox', captured['cmd'])
        self.assertIn('read-only', captured['cmd'])
        self.assertIn('--skip-git-repo-check', captured['cmd'])
        self.assertIn('--output-schema', captured['cmd'])
        self.assertIn('--output-last-message', captured['cmd'])
        self.assertIn('--json', captured['cmd'])
        self.assertEqual(captured['cmd'][-1], '-')
        self.assertIn('Analyze this conversation.', captured['input'])
        self.assertIn('User: hello', captured['input'])
        self.assertEqual(captured['timeout'], 300)

        self.assertEqual(result.patterns, ['Uses Codex'])
        self.assertEqual(result.decisions, ['Added Codex support'])
        self.assertEqual(result.todos, ['Run tests'])
        self.assertEqual(result.summary, 'Codex support was analyzed.')

        saved_output = self.output_dir / 'analysis_20260527_120000.md'
        self.assertTrue(saved_output.exists())
        self.assertIn('Codex support was analyzed', saved_output.read_text())

    def test_analyze_reports_nonzero_exit(self):
        def fake_run(cmd, input, capture_output, text, timeout):
            return subprocess.CompletedProcess(cmd, 2, stdout='out', stderr='err')

        analyzer = CodexAnalyzer(self.prompt_path)
        with patch('codex_analyzer.subprocess.run', side_effect=fake_run):
            with self.assertRaisesRegex(RuntimeError, 'exit code 2'):
                analyzer.analyze(self.recording_path)

    def test_analyze_reports_missing_codex_cli(self):
        analyzer = CodexAnalyzer(self.prompt_path)
        with patch('codex_analyzer.subprocess.run', side_effect=FileNotFoundError):
            with self.assertRaisesRegex(RuntimeError, 'Codex CLI not found'):
                analyzer.analyze(self.recording_path)


class TestAnalyzerFactory(unittest.TestCase):
    """Tests for provider selection."""

    def setUp(self):
        """Isolate the factory from the real user config.

        The factory's step 1.5 (config-driven agent reuse) reads the real
        ~/.config/samantha-llm/config.json unless SAMANTHA_LLM_CONFIG points
        elsewhere. On any box with default_agent set (e.g. abacus),
        HeadlessAgentAnalyzer would win the ladder and these tests would test
        the machine, not the code. Some tests below use patch.dict(os.environ,
        clear=True), which would wipe an env var set in setUp, so the
        guarantee must be re-applied inside each with-block via the
        `pinned_env` helper: it re-adds SAMANTHA_LLM_CONFIG on top of the
        cleared environment.
        """
        self._tmp = tempfile.TemporaryDirectory()
        self.config_path = Path(self._tmp.name) / 'config.json'
        self._orig_config_env = os.environ.get('SAMANTHA_LLM_CONFIG')
        os.environ['SAMANTHA_LLM_CONFIG'] = str(self.config_path)

    def tearDown(self):
        if self._orig_config_env is None:
            os.environ.pop('SAMANTHA_LLM_CONFIG', None)
        else:
            os.environ['SAMANTHA_LLM_CONFIG'] = self._orig_config_env
        self._tmp.cleanup()

    def pinned_env(self, **overrides):
        """Environment mapping for patch.dict(clear=True) that keeps
        SAMANTHA_LLM_CONFIG pinned to the test config path."""
        env = dict(overrides)
        env['SAMANTHA_LLM_CONFIG'] = str(self.config_path)
        return env

    def write_subconscious_config(self, payload):
        """Write a config.json the factory's step 1.5 will find."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(payload))

    def test_explicit_codex_env_selects_codex(self):
        fake_codex = FakeAnalyzerModule('codex')

        with patch.dict(os.environ, self.pinned_env(SAMANTHA_ANALYZER='codex'), clear=True), \
             patch.object(analyzer_factory, 'HAS_CODEX_ANALYZER', True), \
             patch.object(analyzer_factory, 'codex_analyzer', fake_codex), \
             patch.object(analyzer_factory, 'codex_available', return_value=True):
            analyzer = analyzer_factory.create_best_analyzer(Path('/tmp/prompt.txt'))

        self.assertEqual(analyzer['name'], 'codex')

    def test_config_driven_analyzer_wins_when_configured(self):
        """Step 1.5: subconscious.analyzer_agent beats the legacy ladder."""
        fake_anthropic = FakeAnalyzerModule('anthropic')
        fake_codex = FakeAnalyzerModule('codex')
        self.write_subconscious_config({
            'subconscious': {'analyzer_agent': 'opencode'},
        })

        def fake_create_agent_analyzer(prompt_path, output_dir=None):
            return {'name': 'headless'}, 'opencode'

        fake_headless_module = SimpleNamespace(
            load_subconscious_config=lambda: {
                'analyzer_agent': 'opencode'},
            create_agent_analyzer=fake_create_agent_analyzer,
        )

        with patch.dict(os.environ, self.pinned_env(ANTHROPIC_API_KEY='test-key'), clear=True), \
             patch.object(analyzer_factory, 'HAS_ANTHROPIC_ANALYZER', True), \
             patch.object(analyzer_factory, 'HAS_CODEX_ANALYZER', True), \
             patch.object(analyzer_factory, 'anthropic_analyzer', fake_anthropic), \
             patch.object(analyzer_factory, 'codex_analyzer', fake_codex), \
             patch.object(analyzer_factory, 'codex_available', return_value=True), \
             patch.dict('sys.modules', {'headless_agent_analyzer': fake_headless_module}):
            analyzer = analyzer_factory.create_best_analyzer(Path('/tmp/prompt.txt'))

        self.assertEqual(analyzer['name'], 'headless')

    def test_codex_session_prefers_codex_before_claude(self):
        fake_codex = FakeAnalyzerModule('codex')
        fake_claude = FakeAnalyzerModule('claude')

        with patch.dict(os.environ, self.pinned_env(), clear=True), \
             patch.object(analyzer_factory, 'HAS_ANTHROPIC_ANALYZER', False), \
             patch.object(analyzer_factory, 'HAS_CODEX_ANALYZER', True), \
             patch.object(analyzer_factory, 'HAS_CLAUDE_ANALYZER', True), \
             patch.object(analyzer_factory, 'codex_analyzer', fake_codex), \
             patch.object(analyzer_factory, 'claude_analyzer', fake_claude), \
             patch.object(analyzer_factory, 'codex_available', return_value=True):
            analyzer = analyzer_factory.create_best_analyzer(Path('/tmp/prompt.txt'), agent='codex')

        self.assertEqual(analyzer['name'], 'codex')

    def test_anthropic_api_stays_top_priority_when_configured(self):
        fake_anthropic = FakeAnalyzerModule('anthropic')
        fake_codex = FakeAnalyzerModule('codex')

        with patch.dict(os.environ, self.pinned_env(ANTHROPIC_API_KEY='test-key'), clear=True), \
             patch.object(analyzer_factory, 'HAS_ANTHROPIC_ANALYZER', True), \
             patch.object(analyzer_factory, 'HAS_CODEX_ANALYZER', True), \
             patch.object(analyzer_factory, 'anthropic_analyzer', fake_anthropic), \
             patch.object(analyzer_factory, 'codex_analyzer', fake_codex), \
             patch.object(analyzer_factory, 'codex_available', return_value=True):
            analyzer = analyzer_factory.create_best_analyzer(Path('/tmp/prompt.txt'), agent='codex')

        self.assertEqual(analyzer['name'], 'anthropic')


if __name__ == '__main__':
    unittest.main(verbosity=2)
