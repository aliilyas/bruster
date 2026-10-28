#!/usr/bin/env python3
"""Browser-check the catalog, responsive layout, fixture links, and report imports."""
import argparse
import base64
import contextlib
import copy
import json
import sys
import tempfile
import time
from pathlib import Path

from lab.build import ROOT, build
from lab.client import Client
from lab.runner import run
from lab.server import FixtureServer


def verify(client, expression):
    result = client.call('eval',{'expression':expression})
    if result is not True:
        raise AssertionError(f'Catalog assertion was {result!r}: {expression}')


def check_catalog(binary, site, manifest, output, report_file, transport, server):
    folder = output/transport
    folder.mkdir(parents=True,exist_ok=True)
    temporary_root = '/tmp/opencode' if Path('/tmp/opencode').is_dir() else None
    with tempfile.TemporaryDirectory(prefix='lab-catalog-',dir=temporary_root) as temp:
        # WKWebView suspends animation frames for off-screen windows. This test
        # exercises actual rendered frames after resizing the catalog.
        # These sizes fit the smaller macOS runner desktop, which constrains
        # visible windows to its work area. 960px still exercises desktop CSS.
        client = Client(binary,transport,Path(temp),viewport=(960,640),
                        launch=('--visible',) if sys.platform=='darwin' else ())
        try:
            client.call('navigate',{'url':site,'timeout':20000},timeout=25)
            client.call('wait_for',{'selector':'.case'})
            verify(client,f"document.querySelectorAll('.case').length==={len(manifest['cases'])}")
            # Static cards exist before the manifest fetch and event handlers.
            # Gate that fetch to reproduce early typing deterministically.
            server.control('wait','catalog-manifest')
            verify(client,"document.documentElement.dataset.catalogState==='loading'")
            client.call('fill',{'selector':'#search','value':'ref-duplicate'})
            server.control('release','catalog-manifest')
            client.call('wait_for',{'selector':'html[data-catalog-state="ready"]'})
            verify(client,"document.querySelectorAll('.case').length===1")
            client.call('fill',{'selector':'#search','value':''})
            verify(client,f"document.querySelectorAll('.case').length==={len(manifest['cases'])}")
            verify(client,'document.documentElement.scrollWidth<=innerWidth')
            client.call('fill',{'selector':'#search','value':'ref-duplicate'})
            verify(client,"document.querySelectorAll('.case').length===1")
            client.call('click',{'selector':'.case-actions a[href="#ref-duplicate"]'})
            client.call('wait_for',{'selector':'#detail'})
            verify(client,"document.getElementById('detail').textContent.includes('snapshot')")
            client.call('click',{'selector':'#detail a[target="_blank"]'})
            tabs = client.call('tabs')
            assert len(tabs)==2, tabs
            tab = next(item['tab'] for item in tabs if not item['current'])
            client.call('wait_for',{'tab':tab,'selector':'#a'})
            assert client.call('eval',{'tab':tab,'expression':'__lab.id'})=='ref-duplicate'
            client.call('close_tab',{'tab':tab})
            client.call('click',{'selector':'#detail button'})
            verify(client,"document.getElementById('detail').hidden")
            client.call('fill',{'selector':'#search','value':''})
            client.call('select',{'selector':'#contract','value':'probe'})
            probes = sum(item['contract']=='probe' for item in manifest['cases'])
            verify(client,f"document.querySelectorAll('.case').length==={probes}")
            client.call('select',{'selector':'#environment','value':'server'})
            server_probes = sum(item['contract']=='probe' and 'server' in item['requires'] for item in manifest['cases'])
            verify(client,f"document.querySelectorAll('.case').length==={server_probes}")
            client.call('select',{'selector':'#contract','value':''})
            client.call('select',{'selector':'#environment','value':''})
            client.call('click',{'selector':'button[data-category="References"]'})
            references = sum(item['category']=='References' for item in manifest['cases'])
            verify(client,f"document.querySelectorAll('.case').length==={references}")
            client.call('fill',{'selector':'#search','value':'no-such-fixture'})
            verify(client,"document.querySelector('.empty').textContent.includes('No fixtures')")
            client.call('fill',{'selector':'#search','value':''})
            client.call('click',{'selector':'button[data-category=""]'})
            client.call('upload',{'selector':'#report-file','paths':[str(report_file)]})
            client.call('wait_for',{'text':'Imported 2 observations'})
            verify(client,"document.querySelectorAll('.status-pass').length===2")
            # Invalid imports must preserve the last accepted observations.
            report = json.loads(report_file.read_text(encoding='utf-8'))
            for name in ('revision','unknown','duplicate','status'):
                invalid = copy.deepcopy(report)
                if name=='revision':
                    invalid['provenance']['sourceSha256'] = 'old'
                elif name=='unknown':
                    invalid['results'].append(dict(invalid['results'][0],id='unknown-case'))
                elif name=='duplicate':
                    invalid['results'].append(invalid['results'][0])
                else:
                    invalid['results'][0]['status'] = 'made-up'
                file = Path(temp)/(name+'.json')
                file.write_text(json.dumps(invalid),encoding='utf-8')
                client.call('eval',{'expression':"document.getElementById('report-status').textContent=''"})
                client.call('upload',{'selector':'#report-file','paths':[str(file)]})
                client.call('wait_for',{'text':'Import failed:'})
                # Force another render to catch partially updated internal state.
                client.call('fill',{'selector':'#search','value':'ref-duplicate'})
                verify(client,"document.querySelectorAll('.status-pass').length===2")
                client.call('fill',{'selector':'#search','value':''})
            client.call('upload',{'selector':'#report-file','paths':[str(report_file)]})
            client.call('wait_for',{'text':'Imported 2 observations'})
            for width,height,name in [(375,640,'mobile'),(960,640,'desktop')]:
                client.call('resize',{'width':width,'height':height})
                # GTK can acknowledge the request before WebKit gets its new
                # viewport; animation frames alone do not establish readiness.
                deadline = time.monotonic()+5
                while (size := client.call('eval',{'expression':'[innerWidth,innerHeight]'})) != [width,height]:
                    if time.monotonic() >= deadline:
                        raise AssertionError(f'Catalog viewport stayed at {size}, expected {[width,height]}')
                    time.sleep(.02)
                client.call('eval',{'expression':'(async()=>{scrollTo(0,0);await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))})()'})
                verify(client,'document.documentElement.scrollWidth<=innerWidth')
                shot = client.call('screenshot')
                (folder/(name+'.png')).write_bytes(base64.b64decode(shot['png_base64'],validate=True))
            messages = client.call('console')
            assert not [entry for entry in messages if entry['level']=='error'], messages
        except Exception:
            with contextlib.suppress(Exception):
                shot = client.call('screenshot',timeout=4)
                (folder/'failure.png').write_bytes(base64.b64decode(shot['png_base64'],validate=True))
                snapshot = client.call('snapshot',{'format':'json','max':100},timeout=4)
                (folder/'snapshot.json').write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
            raise
        finally:
            error = client.close()
            (folder/'transcript.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in client.records),encoding='utf-8')
            (folder/'stderr.log').write_text('\n'.join(client.errors),encoding='utf-8')
            if error:
                raise RuntimeError('Catalog browser shutdown failed: '+error)
    print(f'PASS {transport} catalog filters, detail links, report import, and mobile/desktop layout',flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--frameworks',type=Path)
    parser.add_argument('--site-dir',type=Path,default=ROOT/'target/test-lab-ui')
    parser.add_argument('--output',type=Path,default=ROOT/'target/test-lab-ui-results')
    args = parser.parse_args()
    manifest = build(args.site_dir,args.frameworks)
    with FixtureServer(args.site_dir,static_gates={'manifest.json':'catalog-manifest'}) as server:
        # Import actual Bruster observations of one fixture through both transports.
        status = run(args.binary.resolve(),server.url,manifest,args.output/'fixture-checks',
                     patterns=['ref-duplicate'],server=server)
        if status:
            return status
        for transport in ('native','mcp'):
            server.reset()
            check_catalog(args.binary.resolve(),server.url,manifest,args.output,
                          (args.output/'fixture-checks/results.json').resolve(),transport,server)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
