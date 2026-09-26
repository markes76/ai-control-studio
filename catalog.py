#!/usr/bin/env python3
"""Public MCP directory and local registrations. No packages or credentials downloaded."""
import json,re,sys,urllib.request,urllib.parse,datetime,fcntl,os
from pathlib import Path
import switch as routing
ROOT=routing.STATE_ROOT
CACHE=ROOT/'catalog.json'
MANIFEST=ROOT/'catalog-installs.json'
CODE=Path.home()/'.claude.json'
DESKTOP=routing.GATEWAY_PROFILE
SOURCE='https://claude.com/marketplace/connectors-plugins'
def read(p,default):
 return json.loads(p.read_text()) if p.exists() else default

def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 routing.write_atomic(p,routing.dump_json(v))

LOCAL_MS365='local-ms365-softeria'
def catalog():
 c=read(CACHE,{}) if CACHE.exists() else read(Path(__file__).with_name('catalog-seed.json'),{})
 c['entries']=[e for e in c.get('entries',[]) if e['_id']!=LOCAL_MS365]
 c['entries'].append({'_id':LOCAL_MS365,'slug':'ms365-local-softeria','title':'Microsoft 365 — Local (Softeria)','author':'Softeria (independent publisher)','type':'local','recipe':True,'categories':['Productivity','Microsoft 365'],'oneLiner':'Local Microsoft Graph MCP with device-code sign-in; starts in read-only mode.','directoryUrl':'https://github.com/Softeria/ms-365-mcp-server','serverUrl':None})
 guides=read(Path(__file__).with_name('provider-guides.json'),{}).get('guides',[])
 for e in c['entries']:
  e.pop('setupGuide',None)
  guide=next((g for g in guides if g['slug']==e.get('slug') and g['endpoint']==e.get('serverUrl')),None)
  if guide:e['setupGuide']=guide
  if e.get('serverUrl')=='https://microsoft365.mcp.claude.com/mcp':e['localAlternative']=LOCAL_MS365
 return c

def refresh():
 req=urllib.request.Request(SOURCE,headers={'User-Agent':'Mozilla/5.0'})
 with urllib.request.urlopen(req,timeout=40) as r: h=r.read(10_000_000).decode()
 chunks=[]
 for m in re.finditer(r'self\.__next_f\.push\((.*?)\)</script>',h):
  try:
   a=json.loads(m[1])
   if a[0]==1: chunks.append(a[1])
  except (ValueError,IndexError): pass
 s=''.join(chunks); entries={}; dec=json.JSONDecoder()
 for m in re.finditer(r'\{"_id":',s):
  try:
   v,_=dec.raw_decode(s[m.start():])
   if 'serverUrl' in v and 'title' in v and v.get('type') in ('remote','local'): entries[v['_id']]=v
  except ValueError: pass
 # Never silently replace the complete snapshot with a partial directory.
 if len(entries)<len([e for e in catalog().get('entries',[]) if not e.get('recipe')]): raise ValueError('Directory returned fewer entries than the saved snapshot. Kept the saved catalog; retry later.')
 if not entries: raise ValueError('Public directory format changed; saved catalog kept.')
 save(CACHE,{'entries':list(entries.values()),'source':SOURCE,'updated':datetime.datetime.now(datetime.timezone.utc).isoformat()})

def name(e): return 'catalog-'+re.sub(r'[^a-z0-9-]','-',e['slug'].lower())
def definitions(e):
 url=e.get('serverUrl')
 if not isinstance(url,str) or not url.startswith('https://'): raise ValueError('This entry needs provider setup or a desktop extension. Open its setup page; no install command is published in the catalog.')
 transport='sse' if urllib.parse.urlparse(url).path.rstrip('/').endswith('/sse') else 'http'
 code={'type':transport,'url':url};desktop={'name':name(e),'transport':transport,'url':url}
 if url=='https://microsoft365.mcp.claude.com/mcp':
  scope='api://07c030f6-5743-41b7-ba00-0a6e85f37c17/.default offline_access openid email'
  code['oauth']={'scopes':scope,'authServerMetadataUrl':'https://microsoft365.mcp.claude.com/.well-known/oauth-authorization-server'}
  desktop['oauth']={'scope':scope}
 return code,desktop

def listing():
 c=catalog(); owned=read(MANIFEST,{}); local=read(routing.DESKTOP_SETTINGS,{}).get('mcpServers',{}); code=read(CODE,{}).get('mcpServers',{}); desktop=read(DESKTOP,{}).get('managedMcpServers',[])
 for e in c['entries']:
  url=e.get('serverUrl'); n=name(e)
  e['codeInstalled']=bool(url and code.get(n,{}).get('url')==url)
  e['desktopInstalled']=bool(url and any(x.get('name')==n and x.get('url')==url for x in desktop))
  if e.get('type')=='local':
   e['codeInstalled']=n in code and code[n]==owned.get('code:'+n,{}).get('definition')
   e['desktopInstalled']=n in local and local[n]==owned.get('desktop:'+n,{}).get('definition')
   import packages
   metadata=read(ROOT/'downloads'/n/'package.json',{})
   e['downloaded']=bool(metadata and Path(metadata.get('path','')).is_file())
   e['packageVersion']=metadata.get('version')
 return {'ok':True,**c}

def modify(action,ident,targets):
 e=next((e for e in catalog()['entries'] if e['_id']==ident),None)
 if e is None: raise ValueError('Entry missing; refresh the directory.')
 code_def,desktop_def=definitions(e); n=name(e); owned=read(MANIFEST,{})
 paths={'code':CODE,'desktop':DESKTOP}; changes={}
 for target in targets:
  p=paths[target]
  if target=='desktop' and not p.exists(): raise ValueError('Saved Desktop gateway profile is missing. Configure the gateway before adding Desktop MCPs.')
  v=read(p,{})
  if target=='code':
   servers=v.setdefault('mcpServers',{}); existing=servers.get(n)
   expected=code_def
  else:
   servers=v.setdefault('managedMcpServers',[])
   if not isinstance(servers,list): raise ValueError('Desktop managedMcpServers is not a list; configuration kept.')
   existing=next((x for x in servers if x.get('name')==n),None); expected=desktop_def
  key=target+':'+n
  if existing is not None and existing!=expected: raise ValueError('A different configuration already uses '+n+'. Nothing changed.')
  if action=='uninstall' and key not in owned: raise ValueError('This registration was not created by this app; kept it.')
  if target=='code':
   if action=='uninstall': servers.pop(n,None)
   else: servers[n]=expected
  else:
   servers[:]=[x for x in servers if x.get('name')!=n]
   if action!='uninstall': servers.append(expected)
  changes[p]=v
  if action=='uninstall': owned.pop(key,None)
  else: owned[key]={'id':ident,'definition':expected}
 backup=ROOT/'backups'/('mcp-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
 backup.mkdir(parents=True,mode=0o700)
 changes[MANIFEST]=owned
 originals={p:p.read_text() if p.exists() else None for p in changes}
 for i,p in enumerate(changes):
  if p.exists():
   import shutil
   shutil.copy2(p,backup/(str(i)+'-'+p.name))
 written=[]
 try:
  for p,v in changes.items():
   save(p,v); written.append(p)
 except Exception:
  for p in reversed(written):
   if originals[p] is None: p.unlink(missing_ok=True)
   else: routing.write_atomic(p,originals[p])
  raise
 return {'ok':True,'message':'Registration '+('removed' if action=='uninstall' else 'saved')+'. Restart Claude Desktop / start a new Claude Code session. Provider authorization may still be required. Desktop registration applies to your gateway profile.','backup':str(backup)}

def install_recipe(ident,targets):
 import shutil,packages
 if ident!=LOCAL_MS365:raise ValueError('Unknown local recipe.')
 if not targets or any(t not in ('desktop','code') for t in targets):raise ValueError('Choose Desktop and/or CLI.')
 command=shutil.which('npx') or next((str(p) for p in (Path('/opt/homebrew/bin/npx'),Path('/usr/local/bin/npx')) if p.exists()),None)
 if not command:raise ValueError('Node.js / npx is required. No runtime was installed.')
 cfg={'command':command,'args':['-y','@softeria/ms-365-mcp-server@0.156.2','--org-mode','--read-only']}
 e=next(e for e in catalog()['entries'] if e['_id']==ident);n=name(e);owned=read(MANIFEST,{});changes={}
 for t in targets:
  p=routing.DESKTOP_SETTINGS if t=='desktop' else CODE
  data=read(p,{});servers=data.setdefault('mcpServers',{});key=t+':'+n
  previous=servers.get(n)
  if previous is not None and previous!=owned.get(key,{}).get('definition'):raise ValueError('A different MCP already uses '+n+'. Nothing changed.')
  definition={**cfg,**({'type':'stdio'} if t=='code' else {})};servers[n]=definition
  owned[key]={'id':ident,'kind':'local','definition':definition,'version':'0.156.2'};changes[p]=data
 changes[MANIFEST]=owned;backup=packages.transaction(changes)
 return {'ok':True,'message':'Local Microsoft 365 configured (read-only). Restart Desktop / start a new CLI session. The client will download and run Softeria’s pinned npm package on connection. Ask Claude to use the Microsoft 365 login tool, then complete the device-code sign-in. Microsoft tenant approval may be required. Inference routing is unchanged.','backup':backup}

def main():
 ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
 with (ROOT/'catalog.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  a=sys.argv[1:]
  if a[0]=='refresh': refresh(); return listing()
  if a[0]=='list': return listing()
  if a[0] in ('resolve','resolve-refresh','get','import','inspect','install-local'):
   import packages
   if a[0] in ('resolve','resolve-refresh'):return packages.sources(a[1],refresh=a[0]=='resolve-refresh')
   if a[0]=='get':return packages.get(a[1],a[2] if len(a)>2 else None)
   if a[0]=='import':return packages.get(a[1],import_path=a[2])
   if a[0]=='inspect':return packages.inspect(a[1])
   if a[0]=='install-local':return packages.install(a[1],a[2],a[4:],json.loads(sys.stdin.read() if a[3]=='-' else a[3]))
  if a[0] in ('install','uninstall','reinstall'):
   e=next((e for e in catalog()['entries'] if e['_id']==a[1]),{})
   if e.get('type')=='local':
    if e.get('recipe') and a[0]!='uninstall':return install_recipe(a[1],a[2:])
    if a[0]!='uninstall':raise ValueError('Get the local package and approve installation first.')
    import packages
    return packages.uninstall(a[1],a[2:])
   return modify(a[0],a[1],a[2:])
  raise ValueError('Unknown command')
if __name__=='__main__':
 try: print(json.dumps(main()))
 except Exception as e: print(json.dumps({'ok':False,'error':str(e)})); sys.exit(1)
