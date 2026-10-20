"""Evaluate installed R versions against a reviewed R Consortium OSV snapshot.

No network/API guessing: caller supplies a Git checkout and records its revision.
Unsupported matching schemas fail; missing coverage is never reported as clean.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import yaml


def version(value):
    text = str(value)
    if not re.fullmatch(r'\d+(?:[.\-]\d+)*', text):
        raise ValueError(f'Unsupported R version syntax: {text}')
    parts = tuple(int(p) for p in re.split(r'[.\-]', text))
    while parts and parts[-1] == 0:
        parts = parts[:-1]
    return parts


def affected(installed, entry):
    value = version(installed)
    if any(value == version(v) for v in entry.get('versions', [])):
        return True
    for span in entry.get('ranges', []):
        if span['type'] != 'ECOSYSTEM':
            raise ValueError('Unsupported range type; coverage must be reviewed')
        start = None
        for event in span['events']:
            if set(event) == {'introduced'}:
                start = version(event['introduced'])
            elif set(event) == {'fixed'}:
                if start is None:
                    raise ValueError('Fixed event without introduced')
                if start <= value < version(event['fixed']):
                    return True
                start = None
            elif set(event) == {'last_affected'}:
                if start is None:
                    raise ValueError('Last affected event without introduced')
                if start <= value <= version(event['last_affected']):
                    return True
                start = None
            else:
                raise ValueError('Unsupported advisory event')
        if start is not None and value >= start:
            return True
    return False


def scan(inventory, database):
    installed = {p['name']: p['version'] for p in inventory['r']['packages']}
    findings, evaluated, skipped = [], [], []
    digest = hashlib.sha256()
    files = sorted((database / 'vulns').rglob('*.yaml'))
    if not files:
        raise ValueError('Empty advisory database')
    for path in files:
        data = path.read_bytes()
        digest.update(str(path.relative_to(database)).encode() + b'\0' + data)
        advisory = yaml.safe_load(data)
        if advisory.get('withdrawn'):
            skipped.append({'id': advisory['id'], 'reason': 'withdrawn'})
            continue
        for entry in advisory['affected']:
            if entry['package']['ecosystem'] not in ('CRAN', 'Bioconductor'):
                raise ValueError('Unsupported advisory ecosystem')
            name = entry['package']['name']
            # Validate all ranges even when this package is absent.
            match = affected(installed.get(name, '0'), entry)
            evaluated.append({'id': advisory['id'], 'package': name, 'installed': installed.get(name)})
            if name in installed and match:
                findings.append({'id': advisory['id'], 'package': name, 'installed': installed[name],
                                 'summary': advisory.get('summary'), 'severity': advisory.get('severity', 'UNSPECIFIED'),
                                 'references': advisory.get('references', []), 'upstream': advisory.get('upstream', [])})
    revision = subprocess.check_output(['git', '-C', str(database), 'rev-parse', 'HEAD'], text=True).strip()
    return dict(schema=1, database='https://github.com/RConsortium/r-advisory-database', revision=revision,
                database_sha256=digest.hexdigest(), advisory_files=len(files), installed_r_packages=len(installed),
                pinned_cran_packages=inventory['pinned_cran_count'], findings=findings, evaluated=evaluated, skipped=skipped,
                coverage_limits=['Sparse curated CRAN/Bioconductor advisory database; absence is not proof of safety',
                                 'R interpreter/core and OS are not covered by this scan',
                                 'Vendored native/JavaScript dependencies are covered only where explicitly named by these advisories'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory', type=Path)
    parser.add_argument('database', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = scan(json.loads(args.inventory.read_text()), args.database)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'advisory_files': report['advisory_files'], 'revision': report['revision'], 'findings': report['findings']}))
    raise SystemExit(1 if report['findings'] else 0)
