"""Offline tests of the launch guard. All subprocess calls are mocked."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('closeout_deploy_test_module', BASE / 'deploy_closeout.py')
deploy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy)


class DeploymentGuardTests(unittest.TestCase):
    def run_guard_case(self, ssh_result):
        with tempfile.TemporaryDirectory() as directory:
            location = Path(directory)
            payload = {'receipt': {'archive_sha256': 'synthetic-test-only'}}
            kwargs = {'side_effect': ssh_result} if isinstance(ssh_result, Exception) else {'return_value': ssh_result}
            with patch.object(deploy, 'BASE', location), \
                    patch.object(deploy, 'build_payload', return_value=payload), \
                    patch.object(deploy.subprocess, 'run', **kwargs) as ssh, \
                    contextlib.redirect_stdout(io.StringIO()):
                if isinstance(ssh_result, Exception):
                    with self.assertRaises(type(ssh_result)):
                        deploy.main()
                else:
                    self.assertEqual(deploy.main(), ssh_result.returncode)
                with self.assertRaises(FileExistsError):
                    deploy.main()
                self.assertEqual(ssh.call_count, 1)
                marker = json.loads((location / 'deploy-attempt.json').read_text())
                self.assertIs(marker['attempt_consumed'], True)
                self.assertEqual(marker['archive_sha256'], 'synthetic-test-only')

    def test_successful_launch_cannot_be_repeated(self):
        self.run_guard_case(subprocess.CompletedProcess([], 0, stdout='{}', stderr=''))

    def test_ambiguous_timeout_cannot_be_repeated(self):
        self.run_guard_case(subprocess.TimeoutExpired([], 100))

    def test_failed_ssh_cannot_be_repeated(self):
        self.run_guard_case(subprocess.CompletedProcess([], 255, stdout='', stderr='synthetic disconnect'))


if __name__ == '__main__':
    unittest.main()
