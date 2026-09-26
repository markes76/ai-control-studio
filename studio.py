"""Claude Code configuration studio. No configured hooks or plugins are executed by inventory."""
import json,re,sys,hashlib,fcntl,shutil,subprocess,tempfile
from pathlib import Path
import switch as r
import skill_import
BASE=Path.home()/'.claude'
WORK=r.STATE_ROOT/'studio-marketplace'
EVENTS={'PreToolUse','PostToolUse','PostToolUseFailure','Notification','Stop','SubagentStart','SubagentStop','SessionStart','SessionEnd','UserPromptSubmit','PreCompact','PermissionRequest'}
def read(p,default=None):return json.loads(p.read_text()) if p.exists() else (default if default is not None else {})
def slug(s):
 if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',s):raise ValueError('Use lowercase letters, numbers and hyphens for the name.')
 return s
def base(project):
 if not project:return BASE
 p=Path(project).expanduser().resolve()
 if not p.is_dir():raise ValueError('Choose an existing project folder.')
 return p/'.claude'
def inventory(project=''):
 roots=[('User',BASE)] + ([('Project',base(project))] if project else [])
 records=[]
 def scan(label,root,readonly=False):
  for kind,pattern in [('agents','agents/**/*.md'),('shortcuts','commands/**/*.md'),('skills','skills/**/SKILL.md')]:
   paths=list(root.glob(pattern))
   if kind=='skills' and (root/'skills').is_dir():
    paths+=list((root/'skills').glob('*/SKILL.md'))
   for path in sorted(set(paths)):
    if '.trash' in path.parts or any(x.startswith('.import-') for x in path.parts):continue
    synced=kind=='skills' and 'synced' in path.relative_to(root).parts
    if path.is_file():records.append({'kind':kind,'name':path.parent.name if kind=='skills' else path.stem,'path':str(path),'scope':'Claude.ai sync cache' if synced else label,'readonly':readonly or synced})
 for label,root in roots:scan(label,root)
 installed=read(BASE/'plugins/installed_plugins.json',{}).get('plugins',{})
 for name,items in installed.items():
  for item in items if isinstance(items,list) else []:
   if not item.get('installPath'):continue
   path=Path(item.get('installPath',''))
   if path.is_dir():
    records.append({'kind':'plugins','name':name,'path':str(path), 'scope':item.get('scope','user'),'readonly':True,'enabled':read(BASE/'settings.json').get('enabledPlugins',{}).get(name,False)})
    scan('Plugin: '+name,path,True)
 for path in (WORK/'plugins').glob('*'):
  if path.is_dir():
   records.append({'kind':'plugins','name':path.name,'path':str(path),'scope':'Local draft','readonly':False});scan('Draft: '+path.name,path)
 hooks=[]
 for label,root in roots:
  for filename in ['settings.json','settings.local.json']:
   path=root/filename
   if path.exists():hooks.append({'scope':label+' '+filename,'path':str(path),'hooks':read(path).get('hooks',{})})
 for rec in records:
  if rec['kind']=='plugins':
   hp=Path(rec['path'])/'hooks/hooks.json'
   if hp.is_file():hooks.append({'scope':('Plugin: ' if rec['readonly'] else 'Draft: ')+rec['name'],'path':str(hp),'hooks':read(hp).get('hooks',{})})
 return {'ok':True,'records':records,'hooks':hooks,'events':sorted(EVENTS),'note':'Local definitions and cached plugin/account skills. Skills includes legacy slash commands. Session-specific built-in skills and availability must be checked with /skills in Claude Code. Installed/synced caches are read-only.'}
def allowed(path,project):
 p=Path(path).resolve(); inv=inventory(project)
 rec=next((x for x in inv['records'] if Path(x['path']).resolve()==p),None)
 if not rec:raise ValueError('Select an existing item from the current inventory.')
 return p,rec
def commit(path,text,expected=None):
 if path.is_symlink():raise ValueError('Refusing to overwrite a symbolic link.')
 if path.exists() and expected != hashlib.sha256(path.read_bytes()).hexdigest():raise ValueError('File changed since it was opened. Reload before saving.')
 path.parent.mkdir(parents=True,exist_ok=True)
 r.back_up([path]);r.write_atomic(path,text)
def validate(cli,path):
 help_result=subprocess.run([cli,'plugin','validate','--help'],capture_output=True,text=True,timeout=15)
 supports_json='--json' in help_result.stdout
 proc=subprocess.run([cli,'plugin','validate',str(path)]+(['--json'] if supports_json else []),capture_output=True,text=True,timeout=30)
 if supports_json and proc.stdout.strip():
  try:return json.loads(proc.stdout)
  except ValueError:pass
 return {'success':proc.returncode==0,'output':(proc.stdout+proc.stderr).strip()}
def handle(a):
 project=a.get('project','');op=a.get('op','inventory')
 if op.startswith('jev-'):
  import jev
  return jev.handle(a)
 if op=='skill-discover':return skill_import.discover(a['url'],r.STATE_ROOT/'skill-downloads')
 if op=='skill-preview':return skill_import.preview_file(r.STATE_ROOT/'skill-downloads',a['token'],a['candidate'],a['file'])
 if op=='skill-import':
  if a.get('scope') not in ('user','project'):raise ValueError('Choose user or selected project for importing.')
  if a.get('scope')=='project' and not project:raise ValueError('Choose a project first.')
  return skill_import.install(r.STATE_ROOT/'skill-downloads',a['token'],a['candidate'],a['name'],(base(project) if a.get('scope')=='project' else BASE)/'skills')
 if op=='inventory':return inventory(project)
 if op=='sessions':
  cli=shutil.which('claude') or str(Path.home()/'.local/bin/claude')
  args=[cli,'agents','--json','--all']+(['--cwd',project] if project else [])
  proc=subprocess.run(args,capture_output=True,text=True,timeout=20)
  if proc.returncode:raise ValueError('This Claude Code version cannot expose sessions through agents --json. '+proc.stderr.strip())
  return {'ok':True,'sessions':json.loads(proc.stdout)}
 if op=='plugin-validate':
  path,rec=allowed(a['path'],project)
  if rec['kind']!='plugins':raise ValueError('Select a plugin.')
  cli=shutil.which('claude') or str(Path.home()/'.local/bin/claude')
  report=validate(cli,path)
  return {'ok':True,'report':report,'message':'Validation passed.' if report.get('success') else 'Validation found errors. Review the report.'}
 if op=='read':
  path,rec=allowed(a['path'],project)
  if path.is_dir():path=path/'.claude-plugin/plugin.json'
  text=path.read_text();return {'ok':True,'text':text,'hash':hashlib.sha256(path.read_bytes()).hexdigest(),'readonly':rec['readonly']}
 if op=='save':
  kind=a['kind'];name=slug(a['name']);root=base(project) if a.get('scope')=='project' else BASE
  if a.get('scope')=='plugin':
   root,rec=allowed(a['pluginPath'],project)
   if rec['scope']!='Local draft':raise ValueError('Choose a local draft plugin.')
  if a.get('path'):
   path,rec=allowed(a['path'],project)
   if rec['readonly']:raise ValueError('Installed plugin files are read-only. Edit the plugin source instead.')
   if path.is_dir():raise ValueError('Use the plugin manifest editor.')
  elif kind in ('agents','shortcuts','skills'):
   path=root/({'agents':'agents/'+name+'.md','shortcuts':'commands/'+name+'.md','skills':'skills/'+name+'/SKILL.md'}[kind])
  else:raise ValueError('Invalid definition type.')
  text=a['text']
  if kind=='agents':text=re.sub(r'^name:.*$', 'name: '+json.dumps(name),text,count=1,flags=re.M)
  if not text.strip():raise ValueError('Instructions cannot be empty.')
  if kind=='agents' and (not text.startswith('---\n') or not re.search(r'^name:\s*\S',text,re.M) or not re.search(r'^description:\s*\S',text,re.M)):raise ValueError('Agents require YAML frontmatter with name and description.')
  cli=shutil.which('claude')
  if cli:
   with tempfile.TemporaryDirectory() as tmp:
    candidate=Path(tmp);(candidate/'.claude-plugin').mkdir();(candidate/'.claude-plugin/plugin.json').write_text('{"name":"validation-preview","version":"0.1.0"}')
    relative=path.relative_to(root) if not a.get('path') else Path({'agents':'agents/'+name+'.md','shortcuts':'commands/'+name+'.md','skills':'skills/'+name+'/SKILL.md'}[kind])
    sample=candidate/relative;sample.parent.mkdir(parents=True,exist_ok=True);sample.write_text(text)
    result=validate(cli,candidate)
    if not result.get('success'):
     errors=[]
     for section in [result.get('manifest',{})]+result.get('contents',[]):
      errors.extend(x.get('message','Invalid definition') for x in section.get('errors',[]))
     raise ValueError('Claude Code validation failed: '+('; '.join(errors) or result.get('output','Invalid definition')))

  commit(path,text,a.get('hash'));return {'ok':True,'message':'Saved Markdown. Start a new Claude Code session if it does not detect the new definition.','path':str(path)}
 if op=='plugin-create':
  name=slug(a['name']);path=WORK/'plugins'/name
  if path.exists():raise ValueError('A plugin with this name already exists.')
  manifest={'name':name,'description':a['description'],'version':'0.1.0','author':{'name':a.get('author') or 'Local author'}}
  (path/'.claude-plugin').mkdir(parents=True);r.write_atomic(path/'.claude-plugin/plugin.json',r.dump_json(manifest))
  for d in ['agents','commands','skills','hooks','scripts']:(path/d).mkdir()
  r.write_atomic(path/'README.md','# '+name+'\n\n'+a['description']+'\n')
  market=read(WORK/'.claude-plugin/marketplace.json',{'name':'llm-switch-local','owner':{'name':'Local user'},'plugins':[]})
  market['plugins'].append({'name':name,'source':'./plugins/'+name,'description':a['description']})
  (WORK/'.claude-plugin').mkdir(exist_ok=True);r.write_atomic(WORK/'.claude-plugin/marketplace.json',r.dump_json(market))
  return {'ok':True,'path':str(path),'message':'Plugin source created. Add agents, commands and skills to its component folders. Install separately.'}
 if op=='plugin-manifest':
  path,rec=allowed(a['path'],project)
  if rec['readonly'] or not path.is_dir():raise ValueError('Only local draft plugin manifests can be edited.')
  manifest=json.loads(a['text']);slug(manifest.get('name',''))
  if manifest['name']!=path.name:raise ValueError('Keep the plugin name equal to its folder name.')
  commit(path/'.claude-plugin/plugin.json',r.dump_json(manifest),a.get('hash'));return {'ok':True,'message':'Plugin manifest saved.'}
 if op=='plugin-install':
  path,rec=allowed(a['path'],project)
  if rec['scope']!='Local draft':raise ValueError('Select a local draft plugin.')
  cli=shutil.which('claude') or str(Path.home()/'.local/bin/claude')
  listed=subprocess.run([cli,'plugin','marketplace','list','--json'],capture_output=True,text=True,timeout=30)
  if listed.returncode:raise ValueError(listed.stderr.strip() or 'Cannot read configured plugin marketplaces.')
  markets=json.loads(listed.stdout)
  registered=next((x for x in markets if x.get('name')=='llm-switch-local'),None)
  if registered and Path(registered.get('installLocation','')).resolve()!=WORK.resolve():raise ValueError('The llm-switch-local marketplace name is already used by another source.')
  commands=[] if registered else [['plugin','marketplace','add',str(WORK)]]
  commands.append(['plugin','install',path.name+'@llm-switch-local','--scope','user'])
  for args in commands:
   proc=subprocess.run([cli]+args,capture_output=True,text=True,timeout=90)
   if proc.returncode:raise ValueError(proc.stderr.strip() or proc.stdout.strip() or 'Claude plugin installation failed.')
  return {'ok':True,'message':'Plugin installed through Claude Code. Start a new CLI session to load it.'}
 if op=='plugin-toggle':
  path,rec=allowed(a['path'],project)
  if rec['kind']!='plugins' or not rec['readonly']:raise ValueError('Choose an installed plugin.')
  cli=shutil.which('claude') or str(Path.home()/'.local/bin/claude')
  proc=subprocess.run([cli,'plugin','enable' if a['enabled'] else 'disable',rec['name']],capture_output=True,text=True,timeout=30)
  if proc.returncode:raise ValueError(proc.stderr.strip() or proc.stdout.strip() or 'Plugin state change failed.')
  return {'ok':True,'message':'Plugin state updated through Claude Code.'}
 if op=='hooks-edit':
  path=Path(a['path']).resolve()
  if not any(Path(x['path']).resolve()==path for x in inventory(project)['hooks']):raise ValueError('Select a hook configuration from the inventory.')
  if any(Path(x['path']).resolve()==path and x['scope'].startswith('Plugin:') for x in inventory(project)['hooks']):raise ValueError('Installed plugin hooks are read-only.')
  data=read(path);data['hooks']=json.loads(a['text'])
  if not isinstance(data['hooks'],dict):raise ValueError('Hooks must be a JSON object.')
  commit(path,r.dump_json(data),a.get('hash'));return {'ok':True,'message':'Hook configuration updated; unrelated settings preserved.'}
 if op=='hooks-read':
  path=Path(a['path']).resolve()
  if not any(Path(x['path']).resolve()==path for x in inventory(project)['hooks']):raise ValueError('Select a hook configuration from the inventory.')
  return {'ok':True,'text':json.dumps(read(path).get('hooks',{}),indent=2),'hash':hashlib.sha256(path.read_bytes()).hexdigest()}
 if op=='hook-save':
  event=a['event']
  if event not in EVENTS:raise ValueError('Unsupported hook event.')
  item={'type':a['type']}
  if item['type']=='command':item['command']=a['value']
  elif item['type']=='http':
   if not a['value'].startswith('https://'):raise ValueError('Use an HTTPS webhook URL.')
   item['url']=a['value']
  else:raise ValueError('Choose command or HTTP hook.')
  if not a['value'].strip():raise ValueError('Hook target is required.')
  path=(base(project) if a.get('scope')=='project' else BASE)/'settings.json'
  if a.get('scope')=='plugin':
   root,rec=allowed(a['pluginPath'],project)
   if rec['scope']!='Local draft':raise ValueError('Choose a local draft plugin.')
   path=root/'hooks/hooks.json'
  settings=read(path);hooks=settings.setdefault('hooks',{});hooks.setdefault(event,[]).append({'matcher':a.get('matcher',''),'hooks':[item]})
  path.parent.mkdir(parents=True,exist_ok=True);r.back_up([path]);r.write_atomic(path,r.dump_json(settings))
  return {'ok':True,'message':'Hook saved. Claude Code will execute it or send HTTP requests on matching events; it was not executed by this editor.'}
 raise ValueError('Unknown studio action.')
if __name__=='__main__':
 try:
  r.STATE_ROOT.mkdir(parents=True,exist_ok=True)
  with (r.STATE_ROOT/'studio.lock').open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX);print(json.dumps(handle(json.load(sys.stdin))))
 except Exception as e:print(json.dumps({'ok':False,'error':str(e)}));sys.exit(1)
