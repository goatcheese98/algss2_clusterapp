"""Summarize raw Ubuntu findings without suppressing header/source matches.

Kernel advisories on linux-libc-dev do not describe an executing image kernel.
Retain every raw finding and count; the deployment host kernel needs a host scan.
All other HIGH/CRITICAL matches fail this bounded runtime gate for review.
"""
import argparse
from collections import Counter
import json
from pathlib import Path


def summarize(report):
    results = report.get('Results', [])
    os_results = [r for r in results if r.get('Class') == 'os-pkgs']
    if not os_results or report.get('Metadata', {}).get('OS', {}).get('Family') != 'ubuntu':
        raise ValueError('Expected actual Ubuntu OS advisory coverage')
    findings = [v for r in os_results for v in r.get('Vulnerabilities', [])]
    high = [v for v in findings if v['Severity'] in ('HIGH', 'CRITICAL')]
    headers = [v for v in high if v['PkgName'] == 'linux-libc-dev']
    other = [v for v in high if v['PkgName'] != 'linux-libc-dev']
    fields = ('VulnerabilityID', 'PkgName', 'InstalledVersion', 'FixedVersion', 'Severity', 'PrimaryURL')
    return dict(schema=1, os=report['Metadata']['OS'], scanned_packages=sum(len(r.get('Packages', [])) for r in os_results),
                severity_counts=dict(Counter(v['Severity'] for v in findings)),
                non_kernel_header_high_critical=[{k: v.get(k) for k in fields} for v in other],
                kernel_header_high_critical_count=len(headers),
                kernel_header_ids=sorted({v['VulnerabilityID'] for v in headers}),
                limits=['Raw report retains kernel source/header matches; no runtime host kernel is scanned',
                        'Trivy Ubuntu OS coverage does not scan the manually compiled R interpreter or CRAN packages',
                        'Medium/low/unfixed findings remain in the raw report; this gate is not a zero-findings claim'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    summary = summarize(json.loads(args.report.read_text()))
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'kernel_header_ids'}))
    raise SystemExit(1 if summary['non_kernel_header_high_critical'] else 0)
