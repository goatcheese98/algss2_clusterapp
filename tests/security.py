"""Advisory range boundaries and fail-closed coverage checks."""
import importlib.util
import csv
import io
import json
from unittest.mock import patch
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

    def test_checkout_digest_cannot_relabel_image_sources(self):
        tool = module('inventory')
        embedded = Path('scripts/source-lock.tsv').read_bytes()
        rows = list(csv.DictReader(embedded.decode().splitlines(), delimiter='\t'))
        changed_rows = [dict(row) for row in rows]
        digest = changed_rows[0]['sha256']
        changed_rows[0]['sha256'] = ('0' if digest[0] != '0' else '1') + digest[1:]
        buffer = io.StringIO(newline='')
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), delimiter='\t', lineterminator='\n')
        writer.writeheader(); writer.writerows(changed_rows)
        changed = buffer.getvalue().encode()
        self.assertEqual(sum(a != b for a, b in zip(embedded, changed)), 1)
        self.assertEqual([(r['package'], r['version']) for r in rows],
                         [(r['package'], r['version']) for r in changed_rows])
        image_id = 'sha256:' + 'a' * 64  # Explicit unit fixture; actual-image regression runs in CI.
        info = [{'Id': image_id, 'Config': {'Labels': {'org.opencontainers.image.revision': 'fixture'}}}]
        def image_read(image, entrypoint, *args, **kwargs):
            if entrypoint == 'cat' and args == ('/opt/algss2/app/scripts/source-lock.tsv',):
                return embedded
            if entrypoint == 'cat':
                return 'ID=ubuntu\nVERSION_ID="24.04"\n'
            if entrypoint == 'dpkg-query':
                return 'fixture\t1\tamd64\tfixture\t1\tii \n'
            return json.dumps({'version': '4.5.0', 'packages': [
                {'name': r['package'], 'version': r['version'], 'priority': 'CRAN'} for r in rows]})
        with patch.object(tool, 'docker', return_value=json.dumps(info)), \
             patch.object(tool, 'run', side_effect=image_read) as read, \
             patch.object(tool.Path, 'read_bytes', return_value=changed), \
             patch.object(tool, 'write') as write:
            with self.assertRaisesRegex(ValueError, 'Image source lock differs from checkout source lock'):
                tool.inventory('movable:tag', Path('unused-unit-output'))
            read.assert_called_once_with(image_id, 'cat', '/opt/algss2/app/scripts/source-lock.tsv', binary=True)
            write.assert_not_called()

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
