"""Deterministic static site generation and assembly with the existing Pages tree."""
import hashlib
import html
import json
import re
import shutil
import subprocess
from pathlib import Path

from .cases import all_cases


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'tests/site'
METHODS = set('navigate reload back forward url title eval snapshot find screenshot rect click hover fill fill_form type press select check drag upload scroll resize text html attr count wait_for network network_request console dialog cookies set_cookie new_tab tabs switch_tab close_tab close dark light minimize maximize'.split())


def validate(cases):
    ids = set()
    for item in cases:
        id = item['id']
        if not re.fullmatch('[a-z][a-z0-9-]*',id) or id in ids:
            raise ValueError(f'Invalid or duplicate case ID: {id}')
        ids.add(id)
        if item['contract'] not in ('required','probe') or item['tier'] not in ('core','stress'):
            raise ValueError(f'{id}: invalid contract/tier')
        if not item['steps']:
            raise ValueError(f'{id}: no executable steps')
        assertions = 0
        tickets = set()
        for step in item['steps']:
            if 'method' in step:
                if step['method'] not in METHODS:
                    raise ValueError(f'{id}: unknown Bruster method {step["method"]}')
                if 'send' in step:
                    if step['send'] in tickets:
                        raise ValueError(f'{id}: duplicate pending request')
                    tickets.add(step['send'])
            elif 'await' in step:
                if step['await'] not in tickets:
                    raise ValueError(f'{id}: awaiting an unknown request')
                tickets.remove(step['await'])
            elif not any(key in step for key in ('server','restart','assertNoDuplicateReplies')):
                raise ValueError(f'{id}: unknown step {step}')
            assertions += any(key in step for key in ('expect','verify','error','image','assertNoDuplicateReplies'))
        if not assertions or tickets:
            raise ValueError(f'{id}: missing assertion or unconsumed pending request')
    return len(ids)


def provenance():
    files = list((ROOT/'scripts/lab').glob('*.py')) + [ROOT/'scripts/test_lab.py']
    files += [p for p in SOURCE.rglob('*') if p.is_file() and 'node_modules' not in p.parts]
    digest = hashlib.sha256()
    for file in sorted(files):
        if file.exists():
            digest.update(file.relative_to(ROOT).as_posix().encode()+b'\0'+file.read_bytes().replace(b'\r\n',b'\n')+b'\0')
    commit = subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True)
    return {'commit':commit.stdout.strip() if commit.returncode==0 else 'unknown','sourceSha256':digest.hexdigest()}


def script_json(value):
    return json.dumps(value,ensure_ascii=True).replace('<','\\u003c')


def page(item, available):
    title = html.escape(item['id']+' · '+item['title'])
    extra = ''.join(f'<script defer src="../{html.escape(path,quote=True)}"></script>\n'
                    for path in item['scripts'] if path in available)
    setup = item['setup'].replace('</script','<\\/script')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><link rel="icon" href="../assets/icon.svg">
<style>body{{margin:24px;font:16px/1.5 system-ui,sans-serif}}button,input,select,textarea{{font:inherit}}button{{cursor:pointer}}iframe{{width:480px;height:240px}}{item['css']}</style>
<script src="../server-config.js"></script><script src="../fixture.js"></script>
{extra}</head><body>
{item['html']}
<script>
__lab.id={script_json(item['id'])};
window.addEventListener('load',async()=>{{
  try{{
    {setup}
    __lab.ready=true;document.documentElement.dataset.labReady='true';
  }}catch(error){{__lab.error=String(error.stack||error);document.documentElement.dataset.labError='true';}}
}},{{once:true}});
</script></body></html>
'''


def build(output, frameworks=None):
    cases = all_cases()
    validate(cases)
    if frameworks:
        for name in ('react.js','vue.js','svelte.js','LICENSES.txt','versions.json'):
            if not (Path(frameworks)/name).is_file():
                raise ValueError(f'Missing framework build file: {Path(frameworks)/name}')
    output = Path(output).resolve()
    marker = output/'.bruster-test-lab'
    if output.exists() and any(output.iterdir()) and not marker.exists():
        raise ValueError(f'Refusing to replace a non-lab directory: {output}')
    if marker.exists():
        for name in json.loads(marker.read_text()):
            old = (output/name).resolve()
            if not old.is_relative_to(output):
                raise ValueError('Invalid previous build inventory')
            if old.is_file():
                old.unlink()
    output.mkdir(parents=True,exist_ok=True)
    marker.write_text('[]\n')
    for path in SOURCE.rglob('*'):
        if not path.is_file() or 'frameworks' in path.relative_to(SOURCE).parts:
            continue
        if path.suffix not in ('.html','.js','.css','.svg','.txt'):
            continue
        destination = output/path.relative_to(SOURCE)
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,destination)
    available = []
    if frameworks:
        for name in ('react','vue','svelte'):
            source = Path(frameworks)/(name+'.js')
            if not source.is_file():
                raise ValueError(f'Missing framework bundle: {source}')
            destination = output/'frameworks'/source.name
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,destination)
            available.append('frameworks/'+source.name)
        for license_file in Path(frameworks).glob('*.LEGAL.txt'):
            shutil.copyfile(license_file,output/'frameworks'/license_file.name)
        for name in ('LICENSES.txt','versions.json'):
            shutil.copyfile(Path(frameworks)/name,output/'frameworks'/name)
    entries = []
    (output/'cases').mkdir(exist_ok=True)
    for item in cases:
        name = 'cases/'+item['id']+'.html'
        (output/name).write_text(page(item,available),encoding='utf-8')
        entries.append(dict(item,url=name))
    manifest = {'schemaVersion':1,'provenance':provenance(),'frameworks':available,'cases':entries}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'.nojekyll').touch()
    inventory = sorted(p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file() and p!=marker)
    marker.write_text(json.dumps(inventory)+'\n')
    return manifest


def assemble(existing, output, frameworks=None):
    existing, output = Path(existing).resolve(),Path(output).resolve()
    if output.exists() or output==existing or output.is_relative_to(existing):
        raise ValueError('Assembly requires a fresh output directory outside the existing site')
    shutil.copytree(existing,output,ignore=shutil.ignore_patterns('.git'))
    lab = output/'test-lab'
    if lab.exists() and not (lab/'.bruster-test-lab').exists():
        raise ValueError('Existing test-lab path is not owned by this publisher')
    manifest = build(lab,frameworks)
    index = output/'index.html'
    link = '<a data-bruster-test-lab href="test-lab/">Test Lab</a>'
    if index.exists():
        content = index.read_text(encoding='utf-8')
        if 'data-bruster-test-lab' not in content:
            if '</nav>' in content:
                content = content.replace('</nav>',link+'\n</nav>',1)
            elif '</body>' in content:
                content = content.replace('</body>','<p>'+link+'</p></body>',1)
            else:
                content += '\n<p>'+link+'</p>\n'
            index.write_text(content,encoding='utf-8')
    else:
        index.write_text('<!doctype html><title>Bruster</title><h1>Bruster</h1><p>'+link+'</p><a href="benchmarks/">Benchmarks</a>',encoding='utf-8')
    (output/'.nojekyll').touch()
    return manifest
