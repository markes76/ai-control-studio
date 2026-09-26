"""Named gateway profiles, credential references only; preserves legacy storage for migration."""
import json,re,sys,os,subprocess,shlex,urllib.request,importlib
import secret_store
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path.home()/'Library/Application Support/AI Control Studio'
FILE=ROOT/'gateway-profiles.json'
def default():return {'selected':None,'profiles':[]}

def load():return json.loads(FILE.read_text()) if FILE.exists() else default()
def selected():
 d=load();return next((p for p in d['profiles'] if p['id']==d.get('selected')),None)
def helper(p=None):
 p=p or selected()
 if not p:raise ValueError('Configure a gateway profile first.')
 return p['helper'] if p['auth']=='helper' else str(ROOT/('credential-'+p['id']+'.sh'))
def token(p=None):
 p=p or selected();result=subprocess.run([helper(p)],capture_output=True,text=True,timeout=180)
 if result.returncode or not result.stdout.strip():raise ValueError('Credential helper returned no key. Sign in or configure the referenced credential environment variable for GUI apps.')
 return result.stdout.strip()
def local_url(value):
 u=urlparse(value)
 return u.scheme in ('http','https') and u.hostname in ('localhost','127.0.0.1','::1') and not (u.username or u.password or u.query or u.fragment)
def ollama_models(url):
 if not local_url(url):raise ValueError('Ollama discovery requires a localhost endpoint.')
 try:
  with urllib.request.urlopen(url,timeout=10) as response:d=json.load(response)
 except Exception:raise ValueError('Cannot reach local Ollama. Open Ollama and check its address; no models were downloaded.') from None
 ids=[m.get('id') for m in d.get('data',[]) if isinstance(m,dict) and isinstance(m.get('id'),str)]
 if not ids:raise ValueError('Ollama has no available models. Add a suitable tool-capable model in Ollama, then refresh.')
 return {'ok':True,'models':ids}
def check_desktop_gateway(url):
 if not local_url(url):raise ValueError('Ollama Desktop gateway must be local.')
 try:
  with urllib.request.urlopen(url.rstrip('/')+'/_ollama/health',timeout=5) as response:
   if response.status!=204 or response.headers.get('X-Ollama-Claude-Gateway')!='1':raise ValueError()
 except Exception:raise ValueError('Enable Claude in the Ollama menu-bar app first. Its Desktop gateway normally runs on 127.0.0.1:11435; the normal API on 11434 cannot replace it.') from None
def handle(a):
 import switch as r
 d=load();op=a.get('op')
 if op=='profile-models':return ollama_models(a.get('modelsUrl','http://localhost:11434/v1/models'))
 before=r.inspect()
 previous_file=FILE.read_bytes() if FILE.exists() else None
 if op=='profiles':return {'ok':True,**d}
 if op=='profile-select':
  if a['id'] not in [p['id'] for p in d['profiles']]:raise ValueError('Unknown profile.')
  d['selected']=a['id']
 elif op=='profile-save':
  name=a['name'].strip()
  if not name:raise ValueError('Profile name is required.')
  for k in ['claudeUrl','codexUrl']:
   u=urlparse(a[k]);
   if not u.hostname:raise ValueError('Gateway URL must include a hostname.')
   if u.scheme!='https' and not (u.scheme=='http' and u.hostname in ['localhost','127.0.0.1','::1']):raise ValueError('Use HTTPS, or HTTP on localhost, for gateway URLs.')
   if u.username or u.password or u.query or u.fragment:raise ValueError('URLs must not contain credentials, queries or fragments.')
  ident=a.get('id') or __import__('uuid').uuid4().hex
  if not re.fullmatch('[a-zA-Z0-9-]+',ident):raise ValueError('Invalid profile ID.')
  p={'id':ident,'name':name,'kind':a.get('kind','Custom'),'claudeUrl':a['claudeUrl'].rstrip('/'),'codexUrl':a['codexUrl'].rstrip('/'),'auth':a['auth']}
  if a.get('modelsUrl'):
   u=urlparse(a['modelsUrl'])
   if not u.hostname:raise ValueError('Gateway URL must include a hostname.')
   if u.scheme!='https' and not (u.scheme=='http' and u.hostname in ['localhost','127.0.0.1','::1']):raise ValueError('Use HTTPS or localhost for the model discovery URL.')
   if u.username or u.password or u.query or u.fragment:raise ValueError('Model discovery URL must not contain credentials.')
   p['modelsUrl']=a['modelsUrl']
  if p['kind']=='Ollama':
   if not all(local_url(p[k]) for k in ('claudeUrl','codexUrl')) or (p.get('modelsUrl') and not local_url(p['modelsUrl'])):raise ValueError('The Ollama preset supports localhost only. Use a Custom profile with authentication for a remote gateway.')
   if p['auth']!='local':raise ValueError('Local Ollama uses its non-secret placeholder credential.')
   model=a.get('claudeModel','').strip()
   if not model or len(model)>200 or any(c.isspace() for c in model):raise ValueError('Choose an exact Ollama model ID.')
   code_url=a.get('claudeCodeUrl') or p['codexUrl'].removesuffix('/v1')
   if not local_url(code_url):raise ValueError('Ollama Claude Code endpoint must be localhost.')
   p['claudeCodeUrl']=code_url.rstrip('/')
   p['claudeModel']=model
  hp_before=ROOT/('credential-'+p['id']+'.sh');old_helper=hp_before.read_bytes() if hp_before.exists() and p['auth']!='helper' else None
  old_helper_mode=hp_before.stat().st_mode & 0o777 if hp_before.exists() else 0o700
  if p['auth']=='local':
   if p['kind']!='Ollama':raise ValueError('Local placeholder credentials are only supported for localhost Ollama.')
   ROOT.mkdir(parents=True,exist_ok=True);hp=Path(helper(p));r.write_atomic(hp,"#!/bin/sh\nprintf %s ollama\n");hp.chmod(0o700)
  elif p['auth']=='helper':
   h=Path(a['helper']).expanduser()
   if not h.is_absolute() or not h.is_file() or not os.access(h,os.X_OK):raise ValueError('Choose an executable credential helper using its absolute path.')
   p['helper']=str(h)
  elif p['auth']=='environment':
   env=a['env']
   if not re.fullmatch('[A-Z_][A-Z0-9_]*',env):raise ValueError('Use an environment variable name, not an API key.')
   p['env']=env;ROOT.mkdir(parents=True,exist_ok=True)
   # launchctl environment is used as fallback for apps launched from Finder.
   script='#!/bin/sh\nvalue=$(/usr/bin/printenv '+env+')\nif [ -z "$value" ]; then value=$(/bin/launchctl getenv '+env+'); fi\n[ -n "$value" ] || exit 1\nprintf %s "$value"\n'
   hp=Path(helper(p));r.write_atomic(hp,script);hp.chmod(0o700)
  elif p['auth']=='keychain':
   ref=secret_store.reference(a.get('secretRef',''));p['secretRef']=ref['id'];ROOT.mkdir(parents=True,exist_ok=True)
   script='#!/bin/sh\nexec /usr/bin/security find-generic-password -a '+shlex.quote(ref['account'])+' -s '+shlex.quote(ref['service'])+' -w\n'
   hp=Path(helper(p));r.write_atomic(hp,script);hp.chmod(0o700)
  else:raise ValueError('Choose Keychain, helper or environment authentication.')
  d['profiles']=[x for x in d['profiles'] if x['id']!=ident]+[p];d['selected']=ident
 else:raise ValueError('Unknown profile operation.')
 ROOT.mkdir(parents=True,exist_ok=True);r.back_up([FILE]);r.write_atomic(FILE,r.dump_json(d))
 reload_targets=[];applied=None
 if a.get('applyActive') is True and op=='profile-save':
  import codex_switch as c
  cs=c.status();active=before['desktop_gateway'] or before['code_gateway'] or cs['codex_gateway']
  if active:
   try:
    importlib.reload(r);importlib.reload(c)
    import apply_bundle as bundle;importlib.reload(bundle)
    model=p.get('claudeModel') or cs.get('codex_model','')
    if cs['codex_gateway']:
     if model not in c.models()['models']:raise ValueError('Select a model supported by this gateway before applying the active Codex route.')
    desktop_choice=before['desktop_gateway'] if before['desktop_gateway'] or before.get('desktop_mode')=='1p' else None
    applied=bundle.apply(desktop_choice,before['code_gateway'],cs['codex_gateway'],model)
    if desktop_choice is True:reload_targets.append('desktop')
    if cs['codex_gateway']:reload_targets.append('codex')
   except Exception:
    if p['auth']!='helper':
     if old_helper is None:hp_before.unlink(missing_ok=True)
     else:r.write_atomic(hp_before,old_helper.decode());hp_before.chmod(old_helper_mode)
    if previous_file is None:FILE.unlink(missing_ok=True)
    else:r.write_atomic(FILE,previous_file.decode())
    raise
 return {'ok':True,**d,'reloadTargets':reload_targets,'applied':applied,'message':('Profile saved and applied to enabled clients. Review the restart prompt.' if applied else 'Profile selected. Use Connections → Apply changes to change client routing. Saving does not install a proxy.')}
if __name__=='__main__':
 try:print(json.dumps(handle(json.load(sys.stdin))))
 except Exception as e:print(json.dumps({'ok':False,'error':str(e)}));sys.exit(1)
