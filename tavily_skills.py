"""Read-only skill search through the owner's existing Tavily HTTP MCP."""
import json,os,time,subprocess,urllib.request,urllib.error,urllib.parse
from pathlib import Path
TOPICS={'frontend':'frontend UI design','review':'code review','security':'security audit','python':'Python development','javascript':'JavaScript TypeScript development','documents':'Word PDF document creation','spreadsheets':'Excel spreadsheet analysis','presentations':'PowerPoint presentations','research':'web research','writing':'technical writing','cloud':'cloud infrastructure','testing':'software testing','database':'database SQL','automation':'workflow automation','general':'general productivity'}

TOPICS.update({'kubernetes':'Kubernetes incident response and cluster operations','terraform':'Terraform infrastructure as code','docker':'Docker container development','react':'React frontend development','nextjs':'Next.js application development','rust':'Rust development','go':'Go development','java':'Java development','dotnet':'.NET C# development','accessibility':'accessibility WCAG auditing','git':'Git GitHub workflows','marketing':'marketing campaigns','legal':'legal document review','data':'data analytics visualization','powerapps':'Microsoft Power Apps development','dataverse':'Microsoft Dataverse configuration','finance':'financial analysis'})

def configured():
 for path in [Path.home()/'.claude.json',Path.home()/'Library/Application Support/Claude-3p/claude_desktop_config.json',Path.home()/'Library/Application Support/Claude/claude_desktop_config.json']:
  try:
   if any(urllib.parse.urlparse(c.get('url','')).hostname=='mcp.tavily.com' for c in json.loads(path.read_text()).get('mcpServers',{}).values()):return True
  except Exception:pass
 return False

def connection():
 paths=[Path.home()/'.claude.json',Path.home()/'Library/Application Support/Claude-3p/claude_desktop_config.json',Path.home()/'Library/Application Support/Claude/claude_desktop_config.json']
 for path in paths:
  if not path.exists():continue
  data=json.loads(path.read_text())
  for name,c in data.get('mcpServers',{}).items():
   url=c.get('url','');parsed=urllib.parse.urlparse(url)
   if parsed.scheme=='https' and parsed.hostname=='mcp.tavily.com':
    headers=dict(c.get('headers',{}))
    if not any(k.lower()=='authorization' for k in headers) and not urllib.parse.parse_qs(parsed.query).get('tavilyApiKey'):
     key=None
     try:
      import secret_store
      if secret_store.available('tavily'):key=secret_store.read('tavily')
     except ValueError:pass
     if not key:key=os.environ.get('TAVILY_API_KEY')
     if not key and __import__('jev').config().get('reuseClaudeOAuth') is True:
      proc=subprocess.run(['/usr/bin/security','find-generic-password','-s','Claude Code-credentials','-w'],capture_output=True,text=True,timeout=10)
      if proc.returncode==0:
       store=json.loads(proc.stdout).get('mcpOAuth',{})
       for record in store.values():
        if record.get('serverName')==name and record.get('serverUrl','').rstrip('/')==url.rstrip('/') and record.get('accessToken'):
         expires=record.get('expiresAt',0)
         if expires and expires<time.time()*1000:continue
         key=record['accessToken'];break
     if not key:raise ValueError('Tavily needs sign-in. Open /mcp in Claude Code and reconnect Tavily, then retry.')
     headers['Authorization']='Bearer '+key
    return url,headers
 raise ValueError('No Tavily HTTP MCP configured. Add Tavily in Claude Code first: https://docs.tavily.com/documentation/mcp')

class Client:
 def __init__(self):self.url,self.headers=connection();self.ident=0;self.deadline=time.monotonic()+20
 def rpc(self,method,params,notification=False):
  self.ident+=1;payload={'jsonrpc':'2.0','method':method,'params':params}
  if not notification:payload['id']=self.ident
  headers={**self.headers,'Content-Type':'application/json','Accept':'application/json, text/event-stream'}
  req=urllib.request.Request(self.url,data=json.dumps(payload).encode(),headers=headers)
  try:
   with urllib.request.urlopen(req,timeout=max(.5,self.deadline-time.monotonic())) as response:
    if response.headers.get('Mcp-Session-Id'):self.headers['Mcp-Session-Id']=response.headers['Mcp-Session-Id']
    if notification:return {}
    if 'text/event-stream' in response.headers.get('Content-Type',''):
     while True:
      line=response.readline(1024*1024)
      if not line:raise ValueError('Tavily returned no response.')
      if line.startswith(b'data:'):
       obj=json.loads(line[5:])
       if obj.get('id')==payload['id']:break
    else:obj=json.loads(response.read(2*1024*1024))
  except urllib.error.HTTPError as e:
   if e.code in (401,403):raise ValueError('Tavily authorization expired or denied. Reconnect Tavily through Claude Code /mcp.') from None
   raise ValueError('Tavily MCP request failed (HTTP '+str(e.code)+').') from None
  except (urllib.error.URLError,TimeoutError):raise ValueError('Tavily search timed out or is unavailable.') from None
  if 'error' in obj:raise ValueError('Tavily MCP rejected the request.')
  return obj.get('result',{})
 def start(self):
  result=self.rpc('initialize',{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'AI Control Studio skill search','version':'1.0.0'}})
  self.headers['MCP-Protocol-Version']=result.get('protocolVersion','2025-06-18')
  self.rpc('notifications/initialized',{},True)

def search(topic):
 if topic not in TOPICS:topic='general'
 query='Claude Code agent skill SKILL.md '+TOPICS[topic]
 client=Client();client.start()
 tools=client.rpc('tools/list',{}).get('tools',[])
 tool=next((t for t in tools if t.get('name') in ('tavily-search','tavily_search')),None)
 if not tool:raise ValueError('Connected Tavily MCP does not expose a search tool.')
 props=tool.get('inputSchema',{}).get('properties',{})
 wanted={'query':query,'search_depth':'basic','max_results':5,'include_domains':['github.com'],'include_raw_content':False}
 args={k:v for k,v in wanted.items() if k in props}
 result=client.rpc('tools/call',{'name':tool['name'],'arguments':args})
 if result.get('isError'):raise ValueError('Tavily search failed. Check its connection and usage limits.')
 data=result.get('structuredContent',{})
 if not data.get('results'):
  for block in result.get('content',[]):
   if block.get('type')=='text':
    try:
     parsed=json.loads(block.get('text',''))
     if isinstance(parsed,dict) and 'results' in parsed:data=parsed;break
    except ValueError:pass
 found=[];seen=set()
 for item in data.get('results',[]):
  url=item.get('url','');p=urllib.parse.urlparse(url)
  if p.scheme!='https' or p.hostname not in ('github.com','raw.githubusercontent.com') or p.username or p.password:continue
  parts=p.path.strip('/').split('/')
  if p.hostname=='github.com' and (len(parts)<2 or parts[0] in ('topics','collections','search','features','orgs','settings','login')):continue
  if url in seen:continue
  seen.add(url);found.append({'title':str(item.get('title','Skill source'))[:180],'url':url,'description':str(item.get('content',''))[:450],'verified':False})
 return {'query':query,'provider':'Tavily MCP','candidates':found,'message':'Found '+str(len(found))+' possible skill sources. Review the repository and downloaded files before installing. Search results are not verified packages.'}
