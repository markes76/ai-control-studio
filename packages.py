"""Download and inspect MCP bundles; extraction/registration requires explicit approval.
No package scripts or installation hooks are executed by this module.
"""
import json,urllib.request,urllib.error,urllib.parse,hashlib,zipfile,stat,re,os,shutil,tempfile,datetime
from pathlib import Path
import switch as routing
MAX_DOWNLOAD=150*1024*1024
MAX_EXPANDED=500*1024*1024

def entry(ident):
 import catalog as c
 e=next((e for e in c.catalog()['entries'] if e['_id']==ident and e['type']=='local'),None)
 if e is None:raise ValueError('Local extension not found.')
 return e

def sources(ident,refresh=False):
 e=entry(ident)
 import catalog as c
 data=c.read(c.ROOT/'local-sources.json',c.read(Path(__file__).with_name('local-sources.json'),{'entries':[]}))
 r=next((r for r in data['entries'] if r['id']==ident),{})
 if refresh:
  from research_locals import audit
  r=audit(e);data['entries']=[x for x in data['entries'] if x['id']!=ident]+[r]
  c.save(c.ROOT/'local-sources.json',data)
 candidates=[]
 for p in r.get('packages',[]):
  n=p['name'].lower()
  if any(x in n for x in ('win32','win-x','windows','linux','osx-x64','darwin-x64','macos-x64')):continue
  candidates.append(p)
 # Prefer the publisher's latest release assets over old README links.
 release=[p for p in candidates if '/expanded_assets/' in p.get('evidence','')]
 if release:candidates=release
 return {'ok':True,'packages':candidates,'sources':r.get('sources',[]),'repository':r.get('repository'),'note':r.get('note','No publicly downloadable Mac bundle found. Use a publisher-supplied HTTPS .mcpb URL or import a downloaded bundle.'),'configurations':r.get('configurations',[]),'directoryUrl':e['directoryUrl']}

def folder(ident):
 import catalog as c
 return c.ROOT/'downloads'/c.name(entry(ident))

def validate_archive(path):
 with zipfile.ZipFile(path) as z:
  infos=z.infolist()
  if len(infos)>50000 or sum(i.file_size for i in infos)>MAX_EXPANDED:raise ValueError('Bundle exceeds the unpacked size limit.')
  seen=set()
  for i in infos:
   p=Path(i.filename)
   if p.is_absolute() or '..' in p.parts or '\\' in i.filename or ':' in i.filename:raise ValueError('Bundle contains an unsafe path.')
   if i.filename=='.gateway-launcher.py':raise ValueError('Bundle uses a reserved installer filename.')
   if i.filename.casefold() in seen:raise ValueError('Bundle contains duplicate paths.')
   seen.add(i.filename.casefold())
   kind=stat.S_IFMT(i.external_attr>>16)
   if kind not in (0,stat.S_IFREG,stat.S_IFDIR):raise ValueError('Bundle contains symlinks or special files; use the publisher installer.')
  if 'manifest.json' not in z.namelist():raise ValueError('Not an MCP bundle: manifest.json is missing.')
  if z.getinfo('manifest.json').file_size>2_000_000:raise ValueError('Manifest is too large.')
  m=json.loads(z.read('manifest.json'))
  if not isinstance(m,dict) or not isinstance(m.get('server',{}).get('mcp_config'),dict):raise ValueError('Bundle does not contain a launch configuration.')
  if not isinstance(m.get('name'),str) or not isinstance(m.get('version'),str):raise ValueError('Bundle manifest is missing name/version.')
  platforms=m.get('compatibility',{}).get('platforms')
  if platforms and 'darwin' not in platforms:raise ValueError('This bundle does not support macOS.')
  return m

def metadata(ident,path,url):
 import catalog as c
 m=validate_archive(path); digest=hashlib.sha256(path.read_bytes()).hexdigest()
 server=m['server'];conf=server['mcp_config']; conf={**conf,**conf.get('platform_overrides',{}).get('darwin',{})}
 info={'ok':True,'id':ident,'path':str(path),'source':url,'sha256':digest,'bytes':path.stat().st_size,'manifest':m,'command':conf.get('command',''),'args':conf.get('args',[]),'userConfig':m.get('user_config',{}),'tools':[t.get('name','') for t in m.get('tools',[]) if isinstance(t,dict)],'version':m['version'],'signature':'Publisher signature has not been verified by this app.'}
 c.save(folder(ident)/'package.json',info)
 return info

def get(ident,url=None,import_path=None):
 import catalog as c
 f=folder(ident);f.mkdir(parents=True,exist_ok=True,mode=0o700)
 fd,temp=tempfile.mkstemp(dir=f,suffix='.mcpb');os.close(fd);p=Path(temp)
 try:
  if import_path:
   src=Path(import_path)
   if src.stat().st_size>MAX_DOWNLOAD:raise ValueError('Bundle exceeds the download size limit.')
   shutil.copyfile(src,p);url='Imported file: '+str(src)
  else:
   if url is None:
    options=sources(ident)['packages']
    if len(options)!=1:raise ValueError('Choose a package URL from the publisher, or import a downloaded .mcpb file.')
    url=options[0]['url']
   parsed=urllib.parse.urlparse(url)
   if parsed.scheme!='https' or not parsed.netloc or parsed.username or parsed.password:raise ValueError('Use a public HTTPS package URL without credentials.')
   req=urllib.request.Request(url,headers={'User-Agent':'Gateway-MCP-Catalog/1.0'})
   try:
    with urllib.request.urlopen(req,timeout=40) as r,p.open('wb') as out:
     if not r.url.startswith('https://'):raise ValueError('Package redirected to an insecure URL.')
     total=0
     while True:
      data=r.read(128*1024)
      if not data:break
      total+=len(data)
      if total>MAX_DOWNLOAD:raise ValueError('Bundle exceeds the download size limit.')
      out.write(data)
   except urllib.error.HTTPError as err:
    raise ValueError(f'Download returned HTTP {err.code}. The provider may require sign-in. Download the official .mcpb in your browser and choose Import bundle.') from err
  validate_archive(p)
  digest=hashlib.sha256(p.read_bytes()).hexdigest();dest=f/(digest+'.mcpb');os.replace(p,dest);os.chmod(dest,0o600)
  return metadata(ident,dest,url)
 finally:
  p.unlink(missing_ok=True)

def inspect(ident):
 import catalog as c
 info=c.read(folder(ident)/'package.json',{})
 if not info:raise ValueError('Get or import the package first.')
 p=Path(info['path'])
 if p.parent!=folder(ident) or hashlib.sha256(p.read_bytes()).hexdigest()!=info['sha256']:raise ValueError('Downloaded bundle changed. Get the package again.')
 validate_archive(p)
 return info

def launch_config(manifest,path,values):
 raw=manifest['server']['mcp_config'];cfg={k:v for k,v in raw.items() if k!='platform_overrides'}
 override=raw.get('platform_overrides',{}).get('darwin',{})
 cfg.update({k:v for k,v in override.items() if k!='env'});cfg['env']={**raw.get('env',{}),**override.get('env',{})}
 schema=manifest.get('user_config',{});answers={}
 for key,field in schema.items():
  v=values.get(key,field.get('default'))
  if field.get('required') and (v is None or v=='' or v==[]):raise ValueError('Required setting: '+field.get('title',key))
  if v is None and field.get('multiple'):v=[]
  if v is None: v='' if field.get('type') not in ('boolean','number') else False if field.get('type')=='boolean' else 0
  kind=field.get('type','string')
  if field.get('multiple'):
   if not isinstance(v,list):raise ValueError('Setting must be a JSON array: '+key)
  elif kind=='boolean' and not isinstance(v,bool):raise ValueError('Setting must be true or false: '+key)
  elif kind=='number' and (not isinstance(v,(int,float)) or isinstance(v,bool)):raise ValueError('Setting must be a number: '+key)
  elif kind in ('string','directory','file') and not isinstance(v,str):raise ValueError('Setting must be text: '+key)
  answers[key]=v
 directories={'__dirname':str(path),'HOME':str(Path.home()),'DOCUMENTS':str(Path.home()/'Documents'),'DOWNLOADS':str(Path.home()/'Downloads'),'DESKTOP':str(Path.home()/'Desktop'),'pathSeparator':'/','/':'/'}
 def expand(v):
  if isinstance(v,str):
   def sub(m):
    k=m[1];value=answers.get(k[12:]) if k.startswith('user_config.') else directories.get(k)
    if isinstance(value,str) and k.startswith('user_config.'):
     value=re.sub(r'\$\{(HOME|DOCUMENTS|DOWNLOADS|DESKTOP)\}',lambda x:directories[x[1]],value)
    if value is None:raise ValueError('Unsupported manifest variable: '+k)
    if isinstance(value,bool):return str(value).lower()
    if isinstance(value,list):raise ValueError('List setting requires an entire argument placeholder.')
    return str(value)
   return re.sub(r'\$\{([^}]+)\}',sub,v)
  return v
 args=[]
 for a in cfg.get('args',[]):
  match=re.fullmatch(r'\$\{user_config\.([^}]+)\}',a) if isinstance(a,str) else None
  if match and isinstance(answers.get(match[1]),list):args.extend(expand(str(x)) for x in answers[match[1]])
  else:args.append(expand(a))
 command=expand(cfg.get('command',''))
 if not isinstance(command,str) or not command:raise ValueError('Manifest has no command.')
 if command in ('node','python','python3'):
  choices=['/opt/homebrew/bin/'+('python3' if command.startswith('python') else 'node'),shutil.which(command)]
  command=next((p for p in choices if p and Path(p).is_file()),'')
  if not command:raise ValueError('Required runtime is not installed. This app does not install runtimes automatically.')
 elif not Path(command).is_absolute():
  relative=path/command
  if relative.is_file():command=str(relative)
  else:
   executable=shutil.which(command)
   if not executable:raise ValueError('Required command not found: '+command)
   command=executable
 if not Path(command).is_file():raise ValueError('Launch executable is missing: '+command)
 if not all(isinstance(a,str) for a in args):raise ValueError('Manifest arguments must be strings.')
 env={k:expand(v) for k,v in cfg.get('env',{}).items()}
 if not all(isinstance(k,str) and isinstance(v,str) for k,v in env.items()):raise ValueError('Manifest environment must contain strings.')
 cwd=expand(cfg.get('cwd',str(path)))
 if not Path(cwd).is_absolute():cwd=str(path/cwd)
 if not Path(cwd).is_dir():raise ValueError('Working directory is missing: '+cwd)
 launcher=path/'.gateway-launcher.py'
 launcher.write_text('import os, sys\nos.chdir(sys.argv[1])\nos.execvpe(sys.argv[2], sys.argv[2:], os.environ)\n')
 os.chmod(launcher,0o600)
 return {'command':'/opt/homebrew/bin/python3','args':[str(launcher),cwd,command]+args,'env':env}

def transaction(changes):
 import catalog as c
 backup=c.ROOT/'backups'/('local-mcp-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir(parents=True,mode=0o700)
 originals={p:p.read_text() if p.exists() else None for p in changes}
 for i,p in enumerate(changes):
  if p.exists():shutil.copy2(p,backup/(str(i)+'-'+p.name))
 written=[]
 try:
  for p,v in changes.items():c.save(p,v);written.append(p)
 except Exception:
  for p in reversed(written):
   if originals[p] is None:p.unlink(missing_ok=True)
   else:routing.write_atomic(p,originals[p])
  raise
 return str(backup)

def install(ident,digest,targets,values):
 import catalog as c
 info=inspect(ident)
 if info['sha256']!=digest:raise ValueError('Approve the currently downloaded bundle first.')
 if not targets or any(t not in ('desktop','code') for t in targets):raise ValueError('Choose Desktop and/or CLI.')
 m=info['manifest'];e=entry(ident);n=c.name(e)
 dest=c.ROOT/'packages'/n/digest;created=not dest.exists()
 if created:
  dest.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
  stage=Path(tempfile.mkdtemp(dir=dest.parent,prefix='.stage-'))
  try:
   with zipfile.ZipFile(info['path']) as z:
    for i in z.infolist():
     target=stage/i.filename
     if i.is_dir():target.mkdir(parents=True,exist_ok=True);continue
     target.parent.mkdir(parents=True,exist_ok=True)
     with z.open(i) as src,target.open('wb') as out:shutil.copyfileobj(src,out)
     os.chmod(target,0o700 if i.external_attr>>16 & 0o111 else 0o600)
   os.replace(stage,dest)
  finally:
   if stage.exists():shutil.rmtree(stage)
 try:
  cfg=launch_config(m,dest,values);owned=c.read(c.MANIFEST,{});changes={}
  paths={'desktop':routing.DESKTOP_SETTINGS,'code':c.CODE}
  for t in targets:
   p=paths[t]
   if t=='desktop' and not p.exists():raise ValueError('Claude Desktop local configuration is missing.')
   data=c.read(p,{});servers=data.setdefault('mcpServers',{});previous=servers.get(n);key=t+':'+n
   if previous is not None and previous!=owned.get(key,{}).get('definition'):raise ValueError('A different MCP already uses '+n+'. Kept the existing configuration.')
   definition={**cfg,**({'type':'stdio'} if t=='code' else {})};servers[n]=definition
   owned[key]={'id':ident,'definition':definition,'kind':'local','packagePath':str(dest),'sha256':digest,'version':m['version']};changes[p]=data
  changes[c.MANIFEST]=owned;backup=transaction(changes)
 except Exception:
  if created:shutil.rmtree(dest)
  raise
 return {'ok':True,'message':'Local MCP installed and registered. Restart Claude Desktop / start a new CLI session. Configure macOS permissions if prompted. The package has not been executed by this app.','backup':backup}

def uninstall(ident,targets):
 import catalog as c
 n=c.name(entry(ident));owned=c.read(c.MANIFEST,{});changes={}
 for t in targets:
  key=t+':'+n;record=owned.get(key)
  if not record or record.get('kind')!='local':continue
  p=routing.DESKTOP_SETTINGS if t=='desktop' else c.CODE;data=c.read(p,{});servers=data.get('mcpServers',{})
  if n in servers and servers[n]!=record['definition']:raise ValueError('Configuration was changed outside this app; kept it.')
  servers.pop(n,None);owned.pop(key);changes[p]=data
 changes[c.MANIFEST]=owned;backup=transaction(changes)
 return {'ok':True,'message':'Local MCP registrations removed from the selected clients. Downloaded packages are retained for reinstall.','backup':backup}
