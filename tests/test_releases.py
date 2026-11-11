"""Test the Loop release version format."""

from pathlib import Path
import runpy
import unittest

release_version = runpy.run_path(str(
    Path(__file__).resolve().parents[1]
    / "custom_components/nightscout_extended/releases.py"
))["release_version"]


class ReleaseVersionTest(unittest.TestCase):
    def test_build_number_is_ignored(self):
        self.assertEqual(release_version("3.14.12.57"), release_version("v3.14.12"))

    def test_compares_numeric_components(self):
        self.assertGreater(release_version("v3.14.13"), release_version("3.14.9.57"))

    def test_rejects_missing_and_prerelease_versions(self):
        for version in (None, "unknown", "v3.14.13-beta.1"):
            self.assertIsNone(release_version(version))
