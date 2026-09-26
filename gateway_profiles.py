"""Named gateway profiles, credential references only; preserves legacy storage for migration."""
import json,re,sys,os,subprocess,shlex
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
def handle(a):
 import switch as r
 d=load();op=a.get('op')
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
  if p['auth']=='helper':
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
 return {'ok':True,**d,'message':'Profile selected. Use Connections → Apply changes to change client routing. Saving a profile does not contact or install a proxy.'}
if __name__=='__main__':
 try:print(json.dumps(handle(json.load(sys.stdin))))
 except Exception as e:print(json.dumps({'ok':False,'error':str(e)}));sys.exit(1)
