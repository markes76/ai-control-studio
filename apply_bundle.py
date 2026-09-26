"""Apply all client choices together, restoring their files if any client fails."""
import sys,json,fcntl
import switch as r
import codex_switch as c
from pathlib import Path

def apply(desktop,code,codex,model):
 paths=[r.CODE_SETTINGS,r.DESKTOP_SETTINGS,r.PROFILE_META,r.GATEWAY_PROFILE,r.ZSHRC,c.CONFIG,c.STATE,r.STATE_ROOT/'original-desktop-inference.json',r.STATE_ROOT/'original-code-model.json']
 originals={p:p.read_bytes() if p.exists() else None for p in paths}
 try:
  previous=c.status()['codex_gateway']
  result=r.apply(desktop,code)
  if codex or previous:c.apply(codex,model)
  return {'ok':True,**result,**c.status(),'codex_restart_needed':codex or previous!=codex}
 except Exception:
  for path,data in originals.items():
   if data is None:path.unlink(missing_ok=True)
   elif not path.exists() or path.read_bytes()!=data:
    path.parent.mkdir(parents=True,exist_ok=True);r.write_atomic(path,data.decode())
  raise
if __name__=='__main__':
 try:
  r.STATE_ROOT.mkdir(parents=True,exist_ok=True)
  with (r.STATE_ROOT/'switch.lock').open('a') as one,(r.STATE_ROOT/'codex-switch.lock').open('a') as two:
   fcntl.flock(one,fcntl.LOCK_EX);fcntl.flock(two,fcntl.LOCK_EX)
   print(json.dumps(apply(None if sys.argv[1]=='keep' else sys.argv[1]=='on',sys.argv[2]=='on',sys.argv[3]=='on',sys.argv[4])))
 except Exception as e:print(json.dumps({'ok':False,'error':str(e)}));sys.exit(1)
