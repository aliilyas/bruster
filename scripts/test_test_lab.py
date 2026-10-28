"""Publication and runner contracts: detect false passes, broken fixtures, and lost site data."""
import copy
import base64
import contextlib
import io
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from lab.build import assemble, build, validate
from lab.cases import all_cases, command
from lab.client import BrowserError, CommandError
from lab.runner import CaseRunner, grade_image, png_pixels, run, same_json, substitute
from lab.server import FixtureServer


class Catalog(unittest.TestCase):
    def test_each_case_has_an_independent_identity_and_assertion(self):
        cases = all_cases()
        self.assertGreaterEqual(validate(cases),300)
        duplicate = copy.deepcopy(cases[:1])*2
        with self.assertRaisesRegex(ValueError,'duplicate'):
            validate(duplicate)
        empty = copy.deepcopy(cases[:1])
        empty[0]['steps'] = [command('click',{'selector':'button'})]
        with self.assertRaisesRegex(ValueError,'missing assertion'):
            validate(empty)

    def test_build_is_reproducible_and_framework_absence_is_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a,b = root/'a',root/'b'
            manifest = build(a)
            build(b)
            first = {p.relative_to(a).as_posix():p.read_bytes() for p in a.rglob('*') if p.is_file()}
            second = {p.relative_to(b).as_posix():p.read_bytes() for p in b.rglob('*') if p.is_file()}
            self.assertEqual(first,second)
            self.assertEqual(manifest['frameworks'],[])
            self.assertIn('framework:react',next(c for c in manifest['cases'] if c['id']=='framework-react')['requires'])
            self.assertNotIn('../frameworks/react.js',(a/'cases/framework-react.html').read_text())
            build(a)  # A rebuild is idempotent, including its owned file inventory.
            self.assertEqual(first,{p.relative_to(a).as_posix():p.read_bytes() for p in a.rglob('*') if p.is_file()})

    def test_assembly_keeps_docs_history_domain_and_adds_one_lab_link(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old = root/'old'
            old.mkdir()
            (old/'index.html').write_text('<html><body><nav><a href="benchmarks/">Benchmarks</a></nav>Documentation</body></html>')
            (old/'CNAME').write_text('example.test')
            (old/'benchmarks').mkdir()
            (old/'benchmarks/history.json').write_text('[{"run":1}]')
            (old/'.git').mkdir()
            (old/'.git/config').write_text('checkout credentials')
            assemble(old,root/'first',base_url='https://example.test/')
            assemble(root/'first',root/'second',base_url='https://example.test/')
            for directory in (root/'first',root/'second'):
                self.assertEqual((directory/'CNAME').read_text(),'example.test')
                self.assertEqual((directory/'benchmarks/history.json').read_text(),'[{"run":1}]')
                self.assertEqual((directory/'index.html').read_text().count('data-bruster-test-lab'),1)
                self.assertFalse((directory/'.git').exists())
                self.assertTrue((directory/'test-lab/cases/select-invalid-multi.html').is_file())
                self.assertEqual([item.text for item in ET.parse(directory/'sitemap.xml').findall('.//{*}loc')],
                                 ['https://example.test/test-lab/'])
            self.assertNotIn('data-bruster-test-lab',(old/'index.html').read_text())

    def test_build_does_not_replace_an_unowned_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path/'notes.txt').write_text('user work')
            with self.assertRaisesRegex(ValueError,'non-lab'):
                build(path)
            self.assertEqual((path/'notes.txt').read_text(),'user work')


class HTTPFixtures(unittest.TestCase):
    def test_static_routes_origin_config_errors_and_post_echo(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'site'
            build(root)
            with FixtureServer(root) as server:
                with urlopen(server.url+'cases/ref-duplicate.html') as response:
                    self.assertIn(b'ref-duplicate',response.read())
                with urlopen(server.url+'server-config.js') as response:
                    self.assertIn(server.other_origin.encode(),response.read())
                with urlopen(server.url+'__lab/redirect?count=3') as response:
                    self.assertEqual(response.url,server.url+'support/other.html')
                request = Request(server.url+'__lab/echo',data=b'payload',headers={'X-Lab':'test'},method='POST')
                with urlopen(request) as response:
                    data = json.load(response)
                    self.assertEqual((data['method'],data['body'],data['headers']['x-lab']),('POST','payload','test'))
                for path in ('does-not-exist.html','%2e%2e/secret','__lab/status?code=500'):
                    with self.assertRaises(HTTPError) as raised:
                        urlopen(server.url+path)
                    raised.exception.close()


class FakeClient:
    response = None
    failure = None
    verification = True

    def __init__(self,*args):
        self.records,self.errors,self.duplicates = [],[],[]

    def call(self,method,params=None,**kwargs):
        expression = (params or {}).get('expression','')
        if method=='eval':
            if 'userAgent:navigator' in expression:
                return {'dpr':1}
            if expression.startswith('(async (result) =>'):
                return self.verification
            return True
        if method=='click':
            if self.failure:
                raise self.failure if isinstance(self.failure, Exception) else CommandError(self.failure)
            return self.response
        return None

    def close(self):
        return None


class Grading(unittest.TestCase):
    def run_fake(self,step,contract='required',**behavior):
        item = {'id':'grading','title':'Grading','category':'Harness','contract':contract,
                'requires':[],'launch':[],'viewport':[960,640],'url':'cases/grading.html','steps':[step]}
        with tempfile.TemporaryDirectory() as temp:
            with patch('lab.runner.Client',FakeClient):
                with patch.multiple(FakeClient,response=None,failure=None,verification=True,**{}):
                    for name,value in behavior.items():
                        setattr(FakeClient,name,value)
                    return CaseRunner('/unused','http://localhost/',{},temp).run_case(item,'native')

    def test_command_success_does_not_override_failed_state_assertion(self):
        result = self.run_fake(command('click',verify='false'),verification=False)
        self.assertEqual(result['status'],'fail')

    def test_expected_errors_must_occur_and_match(self):
        for behavior in ({},{'failure':'unrelated failure'}):
            result = self.run_fake(command('click',error='disabled'),**behavior)
            self.assertEqual(result['status'],'fail')
        result = self.run_fake(command('click',error='disabled'),failure='target is disabled')
        self.assertEqual(result['status'],'pass')

    def test_probe_failure_is_retained_and_boolean_is_not_number(self):
        result = self.run_fake(command('click',expect=True),contract='probe',response=1)
        self.assertEqual(result['status'],'probe-fail')
        self.assertFalse(same_json(True,1))

    def test_transport_failure_cannot_satisfy_an_expected_command_error(self):
        result = self.run_fake(command('click',error=''),failure=BrowserError('Bruster stdout closed'))
        self.assertEqual(result['status'],'error')

    def test_structured_captures_keep_types(self):
        self.assertEqual(substitute({'clip':'{{rect}}','tab':'{{tab}}','url':'{{site}}x'},
                                    {'rect':{'x':1},'tab':2,'site':'http://localhost/'}),
                         {'clip':{'x':1},'tab':2,'url':'http://localhost/x'})

    def test_exit_codes_preserve_skips_and_strict_probe_failures(self):
        item = {'id':'grading','title':'Grading','category':'Harness','contract':'probe','tier':'core',
                'requires':[],'launch':[],'viewport':[960,640],'url':'cases/grading.html',
                'steps':[command('click',expect=True)]}
        manifest = {'provenance':{'sourceSha256':'fixture'},'frameworks':[],'cases':[item]}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary = root/'binary'
            binary.write_text('unused test launcher')
            with patch('lab.runner.Client',FakeClient), contextlib.redirect_stdout(io.StringIO()):
                with patch.multiple(FakeClient,response=None,failure=None,verification=True):
                    self.assertEqual(run(binary,'http://localhost/',manifest,root/'normal',transport='native'),0)
                    self.assertEqual(run(binary,'http://localhost/',manifest,root/'strict',transport='native',strict_probes=True),1)
                item['requires'] = ['server']
                self.assertEqual(run(binary,'http://localhost/',manifest,root/'skipped',transport='native'),2)
            self.assertEqual(json.loads((root/'skipped/results.json').read_text())['summary'],{'skip':1})


class Screenshots(unittest.TestCase):
    @staticmethod
    def sample():
        def chunk(kind,data):
            return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
        # Two RGB rows, encoded independently: Sub then Up. Pixel colors are
        # red/green on top and blue/white below, rather than uniform filler.
        rows = bytes([1,255,0,0,1,255,0, 2,1,0,255,255,0,255])
        return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',2,2,8,2,0,0,0))
                +chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b''))

    def test_pixels_dimensions_and_device_scale_are_asserted(self):
        data = self.sample()
        width,height,pixel = png_pixels(data)
        self.assertEqual((width,height),(2,2))
        self.assertEqual([pixel(0,0),pixel(1,0),pixel(0,1),pixel(1,1)],
                         [[255,0,0],[0,255,0],[0,0,255],[255,255,255]])
        result = {'png_base64':base64.b64encode(data).decode()}
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'capture.png'
            grade_image(result,{'cssWidth':1,'cssHeight':1,'samples':[[.5,.5,[255,255,255]]]},2,output)
            self.assertEqual(output.read_bytes(),data)
            with self.assertRaisesRegex(AssertionError,'Pixel'):
                grade_image(result,{'samples':[[0,0,[0,0,0]]]},1,output)
            with self.assertRaisesRegex(AssertionError,'minimum'):
                grade_image(result,{'minWidth':3},1,output)

    def test_truncated_or_corrupt_png_cannot_pass(self):
        data = self.sample()
        with self.assertRaisesRegex(AssertionError,'end chunk'):
            png_pixels(data[:-12])
        changed = bytearray(data)
        changed[29] ^= 1
        with self.assertRaisesRegex(AssertionError,'checksum'):
            png_pixels(changed)


if __name__=='__main__':
    unittest.main()
