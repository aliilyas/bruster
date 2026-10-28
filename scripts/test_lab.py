#!/usr/bin/env python3
"""Build, serve, publish, and run the Bruster test lab (Python 3.10+, stdlib only)."""
import argparse
import json
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from lab.build import ROOT, assemble, build, validate
from lab.cases import all_cases
from lab.runner import run
from lab.server import FixtureServer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command',required=True)
    for name in ('build','serve','run','assemble','validate'):
        sub = commands.add_parser(name)
        if name in ('build','serve','run','assemble'):
            sub.add_argument('--frameworks',type=Path,help='Directory containing locally built React/Vue/Svelte bundles')
        if name in ('build','serve','run'):
            sub.add_argument('--site-dir',type=Path,default=ROOT/'target/test-lab')
        if name=='build':
            sub.add_argument('--output',type=Path,help='Alias for --site-dir')
        if name=='serve':
            sub.add_argument('--port',type=int,default=8080)
        if name=='assemble':
            sub.add_argument('--existing',type=Path,required=True)
            sub.add_argument('--output',type=Path,required=True)
        if name=='run':
            sub.add_argument('--binary',type=Path,required=True)
            sub.add_argument('--transport',choices=['native','mcp','both'],default='both')
            sub.add_argument('--suite',choices=['core','stress','all'],default='core')
            sub.add_argument('--case',action='append',default=[],help='Case ID or glob; repeat to select multiple cases')
            sub.add_argument('--url',help='Run against a published site instead of starting the local server')
            sub.add_argument('--strict-probes',action='store_true')
            sub.add_argument('--output',type=Path,default=ROOT/'target/test-lab-results'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    args = parser.parse_args()
    if args.command=='validate':
        count = validate(all_cases())
        print(f'Validated {count} executable case definitions')
        return 0
    if args.command=='assemble':
        manifest = assemble(args.existing,args.output,args.frameworks)
        print(f'Assembled {len(manifest["cases"])} fixtures at {args.output}/test-lab/')
        return 0
    if args.command=='run' and args.url:
        site = args.url.rstrip('/')+'/'
        with urlopen(site+'manifest.json',timeout=20) as response:
            manifest = json.load(response)
        if manifest.get('schemaVersion')!=1:
            raise ValueError('Unsupported manifest schema')
        validate(manifest['cases'])
        return run(args.binary.resolve(),site,manifest,args.output,transport=args.transport,suite=args.suite,
                   patterns=args.case,strict_probes=args.strict_probes)
    destination = getattr(args,'output',None) if args.command=='build' else None
    destination = destination or args.site_dir
    manifest = build(destination,args.frameworks)
    if args.command=='build':
        print(f'Built {len(manifest["cases"])} fixtures at {destination}')
        return 0
    with FixtureServer(destination,getattr(args,'port',0)) as server:
        if args.command=='serve':
            print(f'Bruster Test Lab: {server.url}',flush=True)
            print(f'Second test origin: {server.other_origin}',flush=True)
            try:
                threading.Event().wait()
            except KeyboardInterrupt:
                pass
            return 0
        return run(args.binary.resolve(),server.url,manifest,args.output,transport=args.transport,suite=args.suite,
                   patterns=args.case,server=server,strict_probes=args.strict_probes)


if __name__=='__main__':
    sys.exit(main())
