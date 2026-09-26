import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
import jev,jev_assist
class AssistTests(unittest.TestCase):
 def setUp(self):
  self.args={'state':'Choose between two documented workflows.','questions':{'route':{'type':'choice','instructions':'Choose the best workflow.','criteria':{'a':'First workflow','b':'Second workflow'}}}}
 def test_native_always_ask_metadata(self):self.assertIs(jev_assist.TOOL['_meta']['anthropic/requiresUserInteraction'],True)
 def test_unsupported_client_no_call(self):
  with self.assertRaises(ValueError):jev_assist.run(self.args,{}, {},call=lambda *a:self.fail('Unexpected API call'))
 def test_decline_no_call(self):
  result=jev_assist.run(self.args,{}, {'elicitation':{}},ask=lambda _:False,call=lambda *a:self.fail('Unexpected API call'))
  self.assertTrue(result['cancelled'])
 def test_accepted_payload(self):
  seen=[]
  def call(state,questions,*args):seen.append(state);return {'route':{'choice':'a','confidence':.8}}
  with patch.object(jev,'record_activity'):
   result=jev_assist.run(self.args,{}, {'elicitation':{}},ask=lambda payload:payload==self.args,call=call)
  self.assertTrue(result['ok']);self.assertEqual(seen,[self.args['state']])
 def test_bad_response_rejected(self):
  with patch.object(jev,'record_activity'),self.assertRaises(ValueError):jev_assist.run(self.args,{'name':'claude-code','version':'2.1.283'}, {},call=lambda *a:{'route':{'choice':'invented','confidence':.9}})
 def test_native_version_guard(self):
  self.assertFalse(jev_assist.native_confirmation({'name':'claude-code','version':'2.1.198'}));self.assertTrue(jev_assist.native_confirmation({'name':'claude-code','version':'2.1.283'}))
if __name__=='__main__':unittest.main()
