"""Advisory range boundaries and fail-closed coverage checks."""
import importlib.util
from pathlib import Path
import unittest


def module(name):
    spec = importlib.util.spec_from_file_location(name, Path('scripts/security') / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


r = module('r_advisories')
os_report = module('os_report')
sources = module('source_lock')


class SecurityTests(unittest.TestCase):
    def test_full_r_names(self):
        versions = sources.versions()
        self.assertEqual(len(versions), 72)
        self.assertEqual(versions['data.table'], '1.17.0')
        self.assertNotIn('table', versions)

    def test_r_numeric_order(self):
        self.assertLess(r.version('4.9.0'), r.version('4.10.4'))
        self.assertEqual(r.version('1.8-4'), r.version('1.8.4.0'))
        with self.assertRaises(ValueError):
            r.version('1.0rc1')

    def test_fixed_boundaries(self):
        entry = {'ranges': [{'type': 'ECOSYSTEM', 'events': [{'introduced': '2.0.2'}, {'fixed': '4.12.0'}]}]}
        self.assertFalse(r.affected('2.0.1', entry))
        self.assertTrue(r.affected('2.0.2', entry))
        self.assertTrue(r.affected('4.10.4', entry))
        self.assertFalse(r.affected('4.12.0', entry))
        self.assertFalse(r.affected('4.13.0', entry))

    def test_last_affected_and_open_range(self):
        entry = {'ranges': [{'type': 'ECOSYSTEM', 'events': [{'introduced': '0'}, {'last_affected': '1.0'}]}]}
        self.assertTrue(r.affected('1.0', entry))
        self.assertFalse(r.affected('1.0.1', entry))
        self.assertTrue(r.affected('9', {'ranges': [{'type': 'ECOSYSTEM', 'events': [{'introduced': '0'}]}]}))
        self.assertTrue(r.affected('1.2', {'versions': ['1.2.0']}))

    def test_unsupported_coverage_fails(self):
        for span in [{'type': 'GIT', 'events': []}, {'type': 'ECOSYSTEM', 'events': [{'limit': '2'}]},
                     {'type': 'ECOSYSTEM', 'events': [{'fixed': '2'}]}]:
            with self.assertRaises(ValueError):
                r.affected('1', {'ranges': [span]})
        with self.assertRaises(ValueError):
            os_report.summarize({'Results': []})

    def test_os_header_findings_remain_visible(self):
        sample = {'Metadata': {'OS': {'Family': 'ubuntu'}}, 'Results': [{'Class': 'os-pkgs', 'Packages': [{}, {}], 'Vulnerabilities': [
            {'VulnerabilityID': 'HEADER', 'PkgName': 'linux-libc-dev', 'Severity': 'CRITICAL'},
            {'VulnerabilityID': 'LIBRARY', 'PkgName': 'libtiff6', 'Severity': 'HIGH'}]}]}
        summary = os_report.summarize(sample)
        self.assertEqual(summary['severity_counts'], {'CRITICAL': 1, 'HIGH': 1})
        self.assertEqual(summary['kernel_header_ids'], ['HEADER'])
        self.assertEqual(summary['non_kernel_header_high_critical'][0]['VulnerabilityID'], 'LIBRARY')


if __name__ == '__main__':
    unittest.main()
