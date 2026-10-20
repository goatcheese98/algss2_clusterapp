"""Cloud container contract: clean image, hardened runtime, R and browser smoke."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument('image')
args = parser.parse_args()
# Explicitly select the cloud-local daemon; retain registry/proxy configuration.
docker_env = {key: value for key, value in os.environ.items() if key not in {
    'DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'}}
docker = ['docker', '--host=unix:///var/run/docker.sock']

def command(arguments, **kwargs):
    return subprocess.run(docker + arguments, env=docker_env, text=True, capture_output=True, timeout=180, **kwargs)

def checked(arguments, **kwargs):
    result = command(arguments, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout.strip()

user = checked(['image', 'inspect', '--format', '{{.Config.User}}', args.image])
assert user == '10001:10001', user
# Invalid configuration must exit, without starting a healthy server.
invalid = command(['run', '--rm', '--network=none', '-e', 'PORT=80', args.image])
assert invalid.returncode != 0 and 'PORT must' in invalid.stderr

container = None
report = {'image': args.image, 'image_id': checked(['image', 'inspect', '--format', '{{.Id}}', args.image]),
    'user': user, 'invalid_port_rejected': True}
try:
    container = checked(['run', '--detach', '--read-only', '--cap-drop=ALL',
        '--security-opt=no-new-privileges', '--pids-limit=128', '--memory=512m', '--cpus=1',
        '--tmpfs', '/tmp:rw,noexec,nosuid,size=67108864',
        '--tmpfs', '/home/shiny:rw,noexec,nosuid,uid=10001,gid=10001,size=16777216',
        '-e', 'PORT=3840', '-p', '127.0.0.1::3840', args.image])
    assert len(container) == 64 and all(c in '0123456789abcdef' for c in container)
    info = json.loads(checked(['inspect', container]))[0]
    assert info['HostConfig']['ReadonlyRootfs'] and info['HostConfig']['CapDrop'] == ['ALL']
    assert any(value.split('=')[0] == 'no-new-privileges' for value in info['HostConfig']['SecurityOpt'])
    assert checked(['exec', container, 'id', '-u']) == '10001'
    checked(['exec', container, 'sh', '-c', 'test ! -w /opt/algss2/app/data/ALGS_Split_2.csv'])
    assert command(['exec', container, 'sh', '-c', 'test -e /opt/algss2/app/rsconnect']).returncode != 0
    assert command(['exec', container, 'sh', '-c', 'test -e /opt/algss2/app/.git']).returncode != 0
    # Exercise the packaged readiness command and wait for Docker's own status.
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        status = checked(['inspect', '--format', '{{.State.Health.Status}}', container])
        if status == 'healthy':
            break
        if checked(['inspect', '--format', '{{.State.Running}}', container]) != 'true':
            raise RuntimeError('Shiny process stopped before readiness')
        time.sleep(1)
    else:
        raise RuntimeError('Container did not become healthy within 120 seconds')
    checked(['exec', container, 'Rscript', '--vanilla', 'scripts/health.R'])
    # A valid but unbound loopback port must not produce a false ready result.
    assert command(['exec', '-e', 'PORT=65534', container, 'Rscript', '--vanilla', 'scripts/health.R']).returncode != 0
    for test in ['tests/runtime.R', 'tests/analysis.R']:
        result = command(['exec', '-i', container, 'Rscript', '--vanilla', '-'], input=Path(test).read_text())
        assert result.returncode == 0, result.stderr
        print(result.stdout, end='', flush=True)
    bindings = json.loads(checked(['inspect', '--format', '{{json .NetworkSettings.Ports}}', container]))
    binding = bindings['3840/tcp'][0]
    assert binding['HostIp'] == '127.0.0.1'
    browser_env = dict(os.environ, SHINY_URL='http://127.0.0.1:' + binding['HostPort'])
    subprocess.run([sys.executable, 'tests/browser.py'], env=browser_env, check=True, timeout=360)
    checked(['stop', '--time=10', container])
    state = json.loads(checked(['inspect', '--format', '{{json .State}}', container]))
    assert not state['Running'] and not state['OOMKilled'] and state['ExitCode'] in (0, 143), state['ExitCode']
    report.update(read_only=True, dropped_capabilities=True, healthy=True, custom_port=3840,
        false_ready_rejected=True, r_tests='passed', browser_cases=8, stop_exit=state['ExitCode'])
    target = Path(os.getenv('RUNTIME_REPORT', 'runtime-report.json'))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
except Exception:
    if container:
        print(command(['logs', container]).stdout, file=sys.stderr)
    raise
finally:
    if container:
        command(['rm', '--force', container])
