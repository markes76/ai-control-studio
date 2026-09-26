"""Reversible Codex provider switch; never stores the gateway key."""
import json,re,sys,tomllib,fcntl,subprocess,urllib.request
from pathlib import Path
import switch as r
ROOT=r.STATE_ROOT
CONFIG=Path.home()/'.codex/config.toml'
STATE=ROOT/'codex-switch.json'
PROVIDER='gateway-switch'
KEYS=('model','model_provider','model_catalog_json')
def models():
 key=r.gp.token()
 req=urllib.request.Request(r.ACTIVE_GATEWAY.get('modelsUrl',r.ACTIVE_GATEWAY['codexUrl']+'/models'),headers={'Authorization':'Bearer '+key})
 with urllib.request.urlopen(req,timeout=20) as response:data=json.load(response)
 ids=[m.get('slug') or m.get('id') for m in data.get('models',data.get('data',[])) if isinstance(m,dict) and isinstance(m.get('slug') or m.get('id'),str)]
 if not ids:raise ValueError('Gateway returned no models. Check the key’s allowed models.')
 return {'ok':True,'models':ids}
def status():
 d=tomllib.loads(CONFIG.read_text() if CONFIG.exists() else '')
 return {'ok':True,'codex_gateway':d.get('model_provider')==PROVIDER,'codex_model':d.get('model','')}
def root_lines(text):
 end=re.search(r'^\s*\[',text,re.M)
 return text[:end.start()] if end else text,text[end.start():] if end else ''
def apply(on,model):
 text=CONFIG.read_text() if CONFIG.exists() else '';d=tomllib.loads(text);old=json.loads(STATE.read_text()) if STATE.exists() else {}
 if on and not model.strip():raise ValueError('Enter an exact model ID from the gateway Models page.')
 if not on and d.get('model_provider')!=PROVIDER:return status()
 if on and d.get('model_provider')!=PROVIDER and PROVIDER in d.get('model_providers',{}):raise ValueError('Reserved gateway provider already exists. Kept your configuration.')
 head,tail=root_lines(text)
 if on and d.get('model_provider')!=PROVIDER:old={'lines':[line for line in head.splitlines(True) if any(re.match(r'^\s*'+k+r'\s*=',line) for k in KEYS)]}
 head=''.join(line for line in head.splitlines(True) if not any(re.match(r'^\s*'+k+r'\s*=',line) for k in KEYS))
 tail=re.sub(r'\n?# BEGIN Gateway CODEX SWITCH\n.*?# END Gateway CODEX SWITCH\n?', '',tail,flags=re.S)
 if on:
  head='model = '+json.dumps(model.strip())+'\nmodel_provider = "'+PROVIDER+'"\n'+head
  tail+='\n# BEGIN Gateway CODEX SWITCH\n[model_providers.gateway-switch]\nname = '+json.dumps(r.ACTIVE_GATEWAY['name'])+'\nbase_url = '+json.dumps(r.ACTIVE_GATEWAY['codexUrl'])+'\nwire_api = "responses"\n[model_providers.gateway-switch.auth]\ncommand = '+json.dumps(r.gp.helper())+'\ntimeout_ms = 180000\nrefresh_interval_ms = 300000\n# END Gateway CODEX SWITCH\n' 
 else:
  if not old:raise ValueError('Original Codex settings are missing; configuration kept.')
  head=''.join(old['lines'])+head
 result=head+tail;tomllib.loads(result)
 CONFIG.parent.mkdir(parents=True,exist_ok=True);ROOT.mkdir(parents=True,exist_ok=True)
 r.back_up([CONFIG,STATE]);r.write_atomic(STATE,json.dumps(old));r.write_atomic(CONFIG,result)
 return status()
if __name__=='__main__':
 try:
  ROOT.mkdir(parents=True,exist_ok=True)
  with (ROOT/'codex-switch.lock').open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   print(json.dumps(status() if sys.argv[1]=='status' else models() if sys.argv[1]=='models' else apply(sys.argv[2]=='on',sys.argv[3] if len(sys.argv)>3 else '')))
 except Exception as e:print(json.dumps({'ok':False,'error':str(e)}));sys.exit(1)
