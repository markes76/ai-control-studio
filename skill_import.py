"""Fetch skill sources for review. Import copies files; no downloaded code is run."""
import io,json,re,shutil,stat,uuid,zipfile,urllib.request,urllib.parse,socket,ipaddress,os
from pathlib import Path,PurePosixPath
from html.parser import HTMLParser
MAX_BYTES=30*1024*1024
MAX_EXPANDED=80*1024*1024
class PublicRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  public_url(newurl)
  return super().redirect_request(req,fp,code,msg,headers,newurl)
class SkillLinks(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag=='a':
   href=dict(attrs).get('href','')
   if href:self.links.append(href)
def public_url(url):
 p=urllib.parse.urlsplit(url)
 if p.scheme!='https' or not p.hostname or p.username or p.password:raise ValueError('Use a public HTTPS URL without embedded credentials.')
 for addr in socket.getaddrinfo(p.hostname,p.port or 443,type=socket.SOCK_STREAM):
  if not ipaddress.ip_address(addr[4][0]).is_global:raise ValueError('Skill downloads require a public internet host.')
 return p
def fetch(url):
 public_url(url)
 req=urllib.request.Request(url,headers={'User-Agent':'LLM-Switch-Skill-Importer','Accept':'application/vnd.github+json'})
 with urllib.request.build_opener(PublicRedirect()).open(req,timeout=30) as response:
  data=response.read(MAX_BYTES+1)
 if len(data)>MAX_BYTES:raise ValueError('Download exceeds the 30 MB limit. Point to a smaller skill repository or a direct SKILL.md URL.')
 return data
def name_ok(name):
 if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',name) or name in ('synced','anthropic-skills'):raise ValueError('Choose a lowercase skill name with letters, numbers and hyphens; reserved names are not allowed.')
 return name
def discover(url,cache):
 p=public_url(url);prefix='';revision='';source=url
 entries={}
 if p.hostname.lower() in ('github.com','www.github.com'):
  parts=[urllib.parse.unquote(x) for x in p.path.strip('/').split('/')]
  if len(parts)<2:raise ValueError('Paste a GitHub repository URL or a skill folder URL.')
  owner,repo=parts[:2];repo=repo.removesuffix('.git')
  if not all(re.fullmatch(r'[A-Za-z0-9_.-]+',x) for x in (owner,repo)):raise ValueError('Invalid GitHub repository URL.')
  root='https://api.github.com/repos/'+owner+'/'+repo
  meta=json.loads(fetch(root));ref=meta['default_branch']
  if len(parts)>2:
   if parts[2] not in ('tree','blob') or len(parts)<4:raise ValueError('Use a repository, tree folder, or blob SKILL.md URL.')
   ref=parts[3];prefix='/'.join(parts[4:])
   if prefix.endswith('/SKILL.md'):prefix=prefix[:-9]
   elif prefix=='SKILL.md':prefix=''
  commit=json.loads(fetch(root+'/commits/'+urllib.parse.quote(ref,safe='')));revision=commit['sha']
  raw=fetch('https://codeload.github.com/'+owner+'/'+repo+'/zip/'+revision)
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   if len(z.infolist())>15000 or sum(x.file_size for x in z.infolist())>MAX_EXPANDED:raise ValueError('Repository is too large for safe skill discovery.')
   for item in z.infolist():
    if item.is_dir():continue
    path=PurePosixPath(item.filename)
    if path.is_absolute() or '..' in path.parts or '\\' in item.filename:raise ValueError('Archive contains an unsafe path.')
    if stat.S_ISLNK(item.external_attr>>16):continue
    rel=PurePosixPath(*path.parts[1:]).as_posix()
    if prefix and not (rel==prefix or rel.startswith(prefix+'/')):continue
    entries[rel]=(z.read(item),bool(item.external_attr>>16 & 0o111))
 else:
  content=fetch(url)
  if len(content)>2*1024*1024:raise ValueError('Direct skill documents must be under 2 MB.')
  text=content.decode('utf-8')
  if not text.startswith('---\n'):
   parser=SkillLinks();parser.feed(text);links=[]
   for href in parser.links:
    link=urllib.parse.urljoin(url,href);parsed=urllib.parse.urlsplit(link)
    if parsed.scheme!='https' or parsed.username or parsed.password:continue
    parts=parsed.path.strip('/').split('/')
    if parsed.path.endswith('/SKILL.md') or (parsed.hostname in ('github.com','www.github.com') and len(parts)>=2 and parts[0] not in ('features','topics','orgs','settings','login')):
     if link not in links:links.append(link)
   if links:return {'ok':True,'sources':links[:20],'message':'Found possible skill sources linked from this page. Choose one to fetch and inspect.'}
   raise ValueError('No SKILL.md document or GitHub skill links found. Use a repository/folder or a raw SKILL.md URL.')
  entries['SKILL.md']=(content,False)
 skills=[x for x in entries if PurePosixPath(x).name=='SKILL.md']
 if not skills:raise ValueError('No SKILL.md files found in this source. Ask the repository maintainer for its Agent Skills folder or a raw SKILL.md link.')
 token=uuid.uuid4().hex;stage=cache/token;stage.mkdir(parents=True,mode=0o700)
 candidates=[]
 for index,skill in enumerate(sorted(skills)):
  folder=str(PurePosixPath(skill).parent);folder='' if folder=='.' else folder
  selected=[x for x in entries if not folder or x==skill or x.startswith(folder+'/')]
  # Nested skills belong to their own entry, not the parent skill package.
  nested=[str(PurePosixPath(x).parent)+'/' for x in skills if x!=skill and (not folder or x.startswith(folder+'/'))]
  selected=[x for x in selected if not any(x.startswith(n) for n in nested)]
  target=stage/str(index);target.mkdir()
  files=[]
  for path in selected:
   rel=PurePosixPath(path).relative_to(folder) if folder else PurePosixPath(path)
   dest=target/str(rel);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(entries[path][0]);dest.chmod(0o700 if entries[path][1] else 0o600);files.append(str(rel))
  if (target/'SKILL.md').stat().st_size>2*1024*1024:raise ValueError('SKILL.md exceeds the 2 MB review limit.')
  text=(target/'SKILL.md').read_text()
  if not text.startswith('---\n') or not re.search(r'^---\s*$',text[4:],re.M):continue
  guess=re.search(r'^name:\s*[\"\']?([a-z0-9][a-z0-9-]*)',text,re.M)
  name=guess.group(1) if guess else PurePosixPath(folder).name or 'imported-skill'
  candidates.append({'id':str(index),'name':name,'sourcePath':skill,'downloadPath':str(target),'files':files,'text':text,'bytes':sum((target/x).stat().st_size for x in files)})
 if not candidates:shutil.rmtree(stage);raise ValueError('Found SKILL.md files but none contain YAML frontmatter.')
 manifest={'source':source,'revision':revision,'candidates':candidates}
 (stage/'manifest.json').write_text(json.dumps(manifest))
 return {'ok':True,'token':token,**manifest,'message':('Repository files fetched at commit '+revision[:12]+'.' if revision else 'Fetched a single Markdown file. Supporting files must be imported from a GitHub folder.')+' Review instructions and supporting files before import.'}
def staged(cache,token,candidate):
 if not re.fullmatch(r'[a-f0-9]{32}',token) or not re.fullmatch(r'\d+',candidate):raise ValueError('Invalid preview selection.')
 stage=cache/token;manifest=json.loads((stage/'manifest.json').read_text())
 chosen=next((x for x in manifest['candidates'] if x['id']==candidate),None)
 if not chosen:raise ValueError('Fetch the skill again before importing.')
 return stage/candidate,chosen,manifest
def preview_file(cache,token,candidate,path):
 root,chosen,_=staged(cache,token,candidate)
 if path not in chosen['files']:raise ValueError('Select a file from the downloaded skill.')
 content=(root/path).read_bytes()
 if len(content)>512*1024:return {'ok':True,'text':'File is too large for inline preview. Review the downloaded folder in Finder.'}
 try:text=content.decode('utf-8')
 except UnicodeDecodeError:text='Binary supporting file; review the downloaded folder in Finder.'
 return {'ok':True,'text':text}
def install(cache,token,candidate,name,skills_root):
 source,chosen,manifest=staged(cache,token,candidate);name_ok(name)
 skills_root=Path(skills_root);skills_root.mkdir(parents=True,exist_ok=True)
 dest=skills_root/name
 if dest.exists() or dest.is_symlink():raise ValueError('A skill with this name already exists. Choose another name; existing skills are never overwritten by import.')
 temp=skills_root/('.import-'+uuid.uuid4().hex)
 try:
  shutil.copytree(source,temp)
  text=(temp/'SKILL.md').read_text()
  if re.search(r'^name:',text,re.M):text=re.sub(r'^name:.*$', 'name: '+name,text,count=1,flags=re.M)
  else:text=text.replace('---\n','---\nname: '+name+'\n',1)
  (temp/'SKILL.md').write_text(text)
  os.rename(temp,dest)
 finally:
  if temp.exists():shutil.rmtree(temp)
 return {'ok':True,'path':str(dest/'SKILL.md'),'message':'Imported '+name+'. Refresh /skills in Claude Code or start a new session. No package scripts were executed.'}
