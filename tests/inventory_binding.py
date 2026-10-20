"""Actual-image regression: same versions, altered checkout digest must fail.

Uses a scratch checkout containing only a modified lock. Never changes the real
checkout or image. Runs the CLI against an immutable image ID, then confirms the
embedded lock is unchanged and no falsely attributed inventory/SBOM was emitted.
"""
import argparse
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('inventory', ROOT / 'scripts/security/inventory.py')
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


def check(image, output):
    info = json.loads(inventory.docker('image', 'inspect', image))[0]
    image_id = info['Id']
    embedded = inventory.run(image_id, 'cat', '/opt/algss2/app/scripts/source-lock.tsv', binary=True)
    original = (ROOT / 'scripts/source-lock.tsv').read_bytes()
    assert original == embedded, 'The valid checkout must match the image before this regression'
    rows = list(csv.DictReader(original.decode().splitlines(), delimiter='\t'))
    baseline = json.loads((output.parent / 'inventory.json').read_text())
    sbom = json.loads((output.parent / 'sbom.cdx.json').read_text())
    components = {c['name']: c for c in sbom['components']}
    assert baseline['image_id'] == image_id
    assert baseline['source_lock_sha256'] == hashlib.sha256(embedded).hexdigest()
    for row in rows:
        component = components[row['package']]
        assert component['hashes'] == [{'alg': 'SHA-256', 'content': row['sha256']}]
        assert {'name': 'algss2:hash-scope', 'value': 'CRAN source archive, not installed binary'} in component['properties']
    altered = [dict(row) for row in rows]
    digest = altered[0]['sha256']
    altered[0]['sha256'] = ('0' if digest[0] != '0' else '1') + digest[1:]
    assert [(r['package'], r['version']) for r in altered] == [(r['package'], r['version']) for r in rows]
    buf = io.StringIO(newline='')
    writer = csv.DictWriter(buf, fieldnames=list(rows[0]), delimiter='\t', lineterminator='\n')
    writer.writeheader(); writer.writerows(altered)
    changed = buf.getvalue().encode()
    # Exactly one digest character changed; versions, URLs and all other bytes stay fixed.
    assert len(changed) == len(original) and sum(a != b for a, b in zip(changed, original)) == 1
    with tempfile.TemporaryDirectory(prefix='algss2-inventory-binding-') as temp:
        scratch = Path(temp)
        (scratch / 'scripts').mkdir()
        (scratch / 'scripts/source-lock.tsv').write_bytes(changed)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/security/inventory.py'), image_id, str(scratch / 'evidence')],
                                cwd=scratch, text=True, capture_output=True)
        assert result.returncode != 0, 'Altered checkout hash was silently attributed to the immutable image'
        assert 'Image source lock differs from checkout source lock' in result.stderr, result.stderr
        assert not (scratch / 'evidence/inventory.json').exists()
        assert not (scratch / 'evidence/sbom.cdx.json').exists()
    assert inventory.run(image_id, 'cat', '/opt/algss2/app/scripts/source-lock.tsv', binary=True) == embedded
    assert json.loads(inventory.docker('image', 'inspect', image_id))[0]['Id'] == image_id
    report = dict(image_id=image_id, source_lock_sha256=hashlib.sha256(embedded).hexdigest(),
                  altered_checkout_sha256=hashlib.sha256(changed).hexdigest(), altered_package=rows[0]['package'],
                  package_versions_unchanged=True, digest_characters_changed=1, mismatch_rejected=True,
                  baseline_hashes_match_image_lock=True, source_not_binary_labels_preserved=True,
                  no_false_inventory_or_sbom=True, image_lock_unchanged=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    check(args.image, args.output)
