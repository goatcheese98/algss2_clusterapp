"""Review helper: fetch exact CRAN sources over verified HTTPS; never run by app.

Hashes attest observed bytes, not an upstream signature. Review and commit the
output before setup trusts it. CRAN Archive/current may serve the same release.
"""
import argparse
import concurrent.futures
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import urllib.error
import urllib.request


def versions():
    return dict(re.findall(r'([A-Za-z][A-Za-z0-9._]*)\s*=\s*"([\d.\-]+)"', Path('scripts/package-versions.R').read_text()))


def fetch(item):
    name, version = item
    filename = f'{name}_{version}.tar.gz'
    urls = [f'https://cran.r-project.org/src/contrib/Archive/{name}/{filename}',
            f'https://cran.r-project.org/src/contrib/{filename}']
    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=90) as response:
                if not response.url.startswith('https://'):
                    raise ValueError('Refusing non-HTTPS redirect')
                data = response.read()
            break
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
    else:
        raise ValueError(f'Missing CRAN source: {filename}')
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        description = archive.extractfile(f'{name}/DESCRIPTION').read().decode()
    assert re.search(rf'^Package: {re.escape(name)}\s*$', description, re.M)
    assert re.search(rf'^Version: {re.escape(version)}\s*$', description, re.M)
    return {'package': name, 'version': version, 'sha256': hashlib.sha256(data).hexdigest(), 'url': url}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='source-lock.candidate.json')
    parser.add_argument('--check', type=Path, help='Compare observed hashes against a reviewed TSV; never update it')
    args = parser.parse_args()
    manifest = versions()
    assert len(manifest) == 72, 'Review manifest coverage before updating lock'
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        sources = list(pool.map(fetch, sorted(manifest.items())))
    result = {'schema': 1, 'origin': 'CRAN HTTPS release archives; observed SHA-256, not publisher signatures', 'sources': sources}
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    if args.check:
        locked = list(csv.DictReader(args.check.read_text().splitlines(), delimiter='\t'))
        identity = lambda rows: sorted((r['package'], r['version'], r['sha256']) for r in rows)
        if identity(locked) != identity(sources):
            raise ValueError('CRAN sources differ from reviewed source lock')
        print('All 72 CRAN source archive digests match the reviewed lock')
    print('SOURCE_LOCK_JSON=' + json.dumps(result, separators=(',', ':')))
