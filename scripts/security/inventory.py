"""Deterministic inventory and CycloneDX 1.6 SBOM from an actual local image.

No timestamps, environment values, host paths or generated UUIDs. Same image and
source lock yield identical JSON. Direct edges only; no inferred dependency graph.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import quote


def docker(*args, binary=False):
    env = os.environ.copy()
    for key in ('DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'):
        env.pop(key, None)
    return subprocess.check_output(['docker', '--host=unix:///var/run/docker.sock', *args], env=env, text=not binary)


def run(image, entrypoint, *args, binary=False):
    return docker('run', '--rm', '--network', 'none', '--read-only',
                  '--tmpfs', '/tmp:rw,nosuid,noexec,size=64m', '--cap-drop=ALL',
                  '--security-opt=no-new-privileges', '--entrypoint', entrypoint, image, *args, binary=binary)


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def inventory(image, output):
    image_info = json.loads(docker('image', 'inspect', image))[0]
    # Pin every read to the inspected immutable ID, even if a tag moves.
    image = image_info['Id']
    lock_bytes = run(image, 'cat', '/opt/algss2/app/scripts/source-lock.tsv', binary=True)
    if lock_bytes != Path('scripts/source-lock.tsv').read_bytes():
        raise ValueError('Image source lock differs from checkout source lock; refusing source hash attribution')
    query = '${binary:Package}\t${Version}\t${Architecture}\t${source:Package}\t${source:Version}\t${db:Status-Abbrev}\n'
    packages = []
    for line in run(image, 'dpkg-query', '-W', '-f=' + query).splitlines():
        name, version, arch, source, source_version, status = line.split('\t')
        if not status.startswith('ii'):
            continue
        packages.append(dict(name=name, version=version, architecture=arch,
                             source=source, source_version=source_version))
    packages.sort(key=lambda p: p['name'])
    r_code = '''p <- installed.packages(noCache = TRUE); p <- p[order(p[, "Package"], p[, "Version"]), , drop = FALSE]; cat(jsonlite::toJSON(list(version = as.character(getRversion()), packages = unname(lapply(seq_len(nrow(p)), function(i) list(name = p[i, "Package"], version = p[i, "Version"], priority = if (is.na(p[i, "Priority"])) "CRAN" else p[i, "Priority"])))), auto_unbox = TRUE))'''
    r = json.loads(run(image, 'Rscript', '--vanilla', '-e', r_code))
    sources = {s['package']: s for s in csv.DictReader(lock_bytes.decode().splitlines(), delimiter='\t')}
    found = {p['name']: p['version'] for p in r['packages']}
    assert len(sources) == 72 and all(found.get(n) == s['version'] for n, s in sources.items())
    distro = dict(line.split('=', 1) for line in run(image, 'cat', '/etc/os-release').splitlines() if '=' in line)
    result = dict(schema=1, image_id=image_info['Id'], revision=image_info['Config'].get('Labels', {}).get('org.opencontainers.image.revision'),
                  os=dict(id=distro['ID'].strip('"'), version=distro['VERSION_ID'].strip('"'), packages=packages),
                  r=r, pinned_cran_count=len(sources), source_lock_sha256=hashlib.sha256(lock_bytes).hexdigest())
    write(output / 'inventory.json', result)
    components = []
    for p in packages:
        purl = f"pkg:deb/ubuntu/{quote(p['name'].split(':')[0], safe='')}@{quote(p['version'], safe='')}?arch={p['architecture']}&distro=ubuntu-{result['os']['version']}"
        components.append(dict(type='library', name=p['name'], version=p['version'], purl=purl, **{'bom-ref': purl}))
    for p in r['packages']:
        purl = (f"pkg:generic/R-{p['name']}@{p['version']}" if p['priority'] == 'base' else
                f"pkg:cran/{p['name']}@{p['version']}")
        c = dict(type='library', name=p['name'], version=p['version'], purl=purl, **{'bom-ref': purl})
        if p['name'] in sources:
            s = sources[p['name']]
            c['hashes'] = [{'alg': 'SHA-256', 'content': s['sha256']}]
            c['externalReferences'] = [{'type': 'distribution', 'url': s['url']}]
            c['properties'] = [{'name': 'algss2:hash-scope', 'value': 'CRAN source archive, not installed binary'}]
        else:
            c['properties'] = [{'name': 'algss2:advisory-coverage', 'value': 'R bundled/base/recommended; outside pinned CRAN source lock'}]
        components.append(c)
    components.append(dict(type='platform', name='R', version=r['version'], **{'bom-ref': 'R-runtime'}))
    sbom = dict(bomFormat='CycloneDX', specVersion='1.6', version=1,
                metadata={'component': {'type': 'container', 'name': 'algss2-runtime', 'version': image_info['Id'], 'bom-ref': 'runtime'}},
                components=components, dependencies=[{'ref': 'runtime', 'dependsOn': [c['bom-ref'] for c in components]}])
    write(output / 'sbom.cdx.json', sbom)
    print(json.dumps({'os_packages': len(packages), 'r_packages': len(r['packages']), 'pinned_cran': len(sources), 'image_id': image_info['Id'],
                      'source_lock_sha256': result['source_lock_sha256']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    inventory(args.image, args.output)
