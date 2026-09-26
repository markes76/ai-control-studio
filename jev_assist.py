"""Bounded Jev decision assistance; client approval is required on every tool call."""
import json,re,time
TOOL={'name':'ask_jev_decision','description':'Ask Jev through OpenRouter for a fast typed choice, binary probability, or score. Explain what specific evidence you propose to send and obtain user approval for THIS request. Never send secrets. This is advice only, not authorization to execute actions.','_meta':{'anthropic/requiresUserInteraction':True},'inputSchema':{'type':'object','properties':{'state':{'type':'string','description':'Minimal evidence for this decision; do not include credentials or unrelated conversation.'},'questions':{'type':'object','description':'Named Jev questions: each has type choice/noul/score, instructions, and criteria (label-to-meaning object, or ordered array for score).'}},'required':['state','questions'],'additionalProperties':False}}
GUIDANCE='Optional Jev decision support is available through the ai-control-skills MCP ask_jev_decision tool. Use it only for bounded choices, routing, scoring or binary assessments, not prose generation. When it would help, explain the specific decision and minimum evidence you propose to send to OpenRouter and ask: Would you like Jev to help with this decision? The tool requires user interaction on each call. Do not call it after the user declines or imply a prior approval covers a later request. Never send secrets or full transcripts. Report the recommendation and confidence; it does not authorize actions. Skill suggestions and Tavily discovery are separate controls.'

def validate(args):
 state=args.get('state');questions=args.get('questions')
 if not isinstance(state,str) or not state.strip() or len(state)>12000:raise ValueError('Provide a specific decision state of 1–12,000 characters.')
 if not isinstance(questions,dict) or not 1<=len(questions)<=8:raise ValueError('Provide 1–8 named decision questions.')
 for name,q in questions.items():
  if not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]{0,63}',name) or not isinstance(q,dict):raise ValueError('Invalid question name or definition.')
  if q.get('type') not in ('choice','noul','score') or not isinstance(q.get('instructions'),str) or not q['instructions'].strip():raise ValueError('Each question requires a supported type and instructions.')
  criteria=q.get('criteria')
  if q['type']=='score':
   if not isinstance(criteria,list) or not 2<=len(criteria)<=20 or not all(isinstance(x,str) and x.strip() for x in criteria):raise ValueError('Scores require 2–20 ordered text criteria.')
  elif not isinstance(criteria,dict) or not 2<=len(criteria)<=20 or not all(isinstance(v,str) and v.strip() for v in criteria.values()):raise ValueError('Choices require 2–20 named text criteria.')
  if q['type']=='noul' and set(criteria)!={'true','false'}:raise ValueError('Binary criteria must be true and false.')
 if len(json.dumps(args))>24000:raise ValueError('Decision request is too large.')
 return state,questions

def native_confirmation(client):
 name=client.get('name','').lower();version=client.get('version','')
 match=re.match(r'^(\d+)\.(\d+)\.(\d+)',version)
 return name in ('claude-code','claude code','claude-code-cli') and match is not None and tuple(map(int,match.groups()))>=(2,1,199)

def run(args,client,capabilities,ask=None,call=None):
 import jev
 state,questions=validate(args)
 if not native_confirmation(client):
  if 'elicitation' not in capabilities or ask is None:raise ValueError('This client cannot enforce per-request consent. Use current Claude Code, which shows an approval prompt for every Jev decision.')
  if not ask({'state':state,'questions':questions}):return {'ok':True,'cancelled':True,'message':'Jev request declined. Nothing was sent to OpenRouter.'}
 started=time.monotonic()
 try:
  answers=(call or jev.decision)(state,questions,time.monotonic()+15,jev.config().get('model',jev.MODEL))
  if set(answers)!=set(questions):raise ValueError('Jev returned unexpected decision questions.')
  for name,q in questions.items():
   answer=answers[name]
   if not isinstance(answer,dict):raise ValueError('Invalid Jev answer.')
   if q['type']=='choice':jev.selected(answer,q['criteria'])
   else:
    value=answer.get('noul' if q['type']=='noul' else 'score')
    if isinstance(value,bool) or not isinstance(value,(int,float)) or (q['type']=='noul' and not 0<=value<=1) or (q['type']=='score' and (int(value)!=value or not 0<=value<len(q['criteria']))):raise ValueError('Jev returned an invalid probability or score.')
  result={'ok':True,'model':jev.config().get('model',jev.MODEL),'answers':answers,'message':'Jev recommendation only. User approval is still needed for consequential actions.'};jev.record_activity('Approved decision assistance',started,result);return result
 except Exception as e:jev.record_activity('Approved decision assistance',started,error=e);raise
