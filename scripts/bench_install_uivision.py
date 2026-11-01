#!/usr/bin/env python3
"""Install the official Ui.Vision Chrome extension in the isolated benchmark directory."""
import argparse
import base64
import hashlib
import io
import json
import re
import struct
import subprocess
import urllib.request
import zipfile
from pathlib import Path


EXTENSION_ID = 'gcbalfbdmfieckjlnblleoemohcganoc'


def fields(data):
    """Read the length-delimited protobuf fields used by CRX3's public header."""
    offset = 0

    def varint():
        nonlocal offset
        value, shift = 0, 0
        while offset < len(data) and shift < 64:
            byte = data[offset]
            offset += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value
            shift += 7
        raise ValueError('Invalid CRX3 header integer')

    while offset < len(data):
        tag = varint()
        if tag & 7 != 2:
            raise ValueError('Unexpected CRX3 header field')
        size = varint()
        end = offset + size
        if end > len(data):
            raise ValueError('Truncated CRX3 header')
        yield tag >> 3, data[offset:end]
        offset = end


def install(chrome, deps):
    version = re.search(r'\d+\.\d+\.\d+\.\d+', subprocess.check_output([str(chrome), '--version'], text=True)).group()
    url = ('https://clients2.google.com/service/update2/crx?response=redirect'
           f'&prodversion={version}&acceptformat=crx3&x=id%3D{EXTENSION_ID}%26uc')
    with urllib.request.urlopen(url, timeout=120) as response:
        data, resolved_url = response.read(), response.url
    if data[:4] != b'Cr24' or struct.unpack('<I', data[4:8])[0] != 3:
        raise ValueError('Expected a CRX3 Chrome Web Store download')
    header_length = struct.unpack('<I', data[8:12])[0]
    key = None
    for number, proof in fields(data[12:12 + header_length]):
        if number not in (2, 3):
            continue
        for field, public_key in fields(proof):
            if field != 1:
                continue
            identifier = ''.join(chr(ord('a') + int(n, 16)) for n in hashlib.sha256(public_key).hexdigest()[:32])
            if identifier == EXTENSION_ID:
                key = base64.b64encode(public_key).decode()
    if key is None:
        raise ValueError('Download does not contain the official Ui.Vision extension identity')
    root = deps / 'uivision-extension'
    root.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        archive.extractall(root)
    manifest = json.loads((root / 'manifest.json').read_text())
    # Preserve the Web Store extension ID when loading the same release unpacked.
    # Its MCP bridge authenticates Chrome extension origins against this ID.
    manifest['key'] = key
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    provenance = {'extension_id': EXTENSION_ID, 'version': manifest['version'], 'source': url,
                  'resolved_url': resolved_url, 'crx_sha256': hashlib.sha256(data).hexdigest(),
                  'setup_change': 'Public CRX key added to manifest to retain the official ID when unpacked',
                  'manifest_sha256': hashlib.sha256((root / 'manifest.json').read_bytes()).hexdigest()}
    (deps / 'uivision-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(provenance, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chrome', type=Path, required=True)
    parser.add_argument('--deps', type=Path, required=True)
    args = parser.parse_args()
    install(args.chrome.resolve(strict=True), args.deps.resolve(strict=True))
