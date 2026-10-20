"""Install exact official scanner bytes; fail closed on SHA-256 mismatch."""
import hashlib
import io
from pathlib import Path
import tarfile
import urllib.request

VERSION = '0.76.0'
SHA256 = 'e24b1c51293c1b15e4ba8d45bbc7891ba053f90278ec2698f3562c993e145fe7'
url = f'https://github.com/aquasecurity/trivy/releases/download/v{VERSION}/trivy_{VERSION}_Linux-64bit.tar.gz'
with urllib.request.urlopen(url, timeout=120) as response:
    if not response.url.startswith('https://'):
        raise ValueError('Refusing non-HTTPS redirect')
    data = response.read()
if hashlib.sha256(data).hexdigest() != SHA256:
    raise ValueError('Official Trivy archive digest mismatch')
Path('.security-tools').mkdir(exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
    member = archive.getmember('trivy')
    if not member.isfile():
        raise ValueError('Scanner binary is not a regular file')
    target = Path('.security-tools/trivy')
    target.write_bytes(archive.extractfile(member).read())
    target.chmod(0o755)
print(f'Installed official Trivy {VERSION}, archive SHA-256 {SHA256}')
