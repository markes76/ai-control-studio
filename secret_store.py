"""Credential references only. Managed secret values are held by macOS Keychain."""
import json,os,subprocess
from pathlib import Path
REGISTRY=Path.home()/'Library/Application Support/AI Control Studio/secret-references.json'
def entries():
 builtins=[{'id':'openrouter','label':'OpenRouter','service':'ai-control-studio.secret.openrouter','account':os.environ.get('USER',''),'readonly':False,'purpose':'Jev decision API'},{'id':'tavily','label':'Tavily API key','service':'ai-control-studio.secret.tavily','account':os.environ.get('USER',''),'readonly':False,'purpose':'Optional Tavily API credential'},{'id':'claude-oauth','label':'Claude Code OAuth credentials','service':'Claude Code-credentials','account':'','readonly':True,'purpose':'Managed by Claude Code; includes MCP sign-ins'}]
 custom=json.loads(REGISTRY.read_text()) if REGISTRY.exists() else []
 for rec in custom:
  if not isinstance(rec,dict) or rec.get('service') != 'ai-control-studio.secret.'+str(rec.get('id','')) or rec.get('id') in {x['id'] for x in builtins}:raise ValueError('Invalid secret reference registry.')
 return builtins+custom
def reference(ident):
 rec=next((x for x in entries() if x['id']==ident),None)
 if not rec or rec.get('readonly'):raise ValueError('Choose a managed API key reference.')
 return rec

def read(ident):
 rec=reference(ident)
 proc=subprocess.run(['/usr/bin/security','find-generic-password','-a',rec['account'],'-s',rec['service'],'-w'],capture_output=True,text=True,timeout=15)
 if proc.returncode or not proc.stdout.strip():raise ValueError('Keychain credential unavailable. Open AI Control Studio → Secret Manager to add it or allow Keychain access.')
 return proc.stdout.strip()
def available(ident):
 try:
  rec=reference(ident)
  return subprocess.run(['/usr/bin/security','find-generic-password','-a',rec['account'],'-s',rec['service']],capture_output=True,timeout=5).returncode==0
 except Exception:return False
