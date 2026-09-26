import unittest,tempfile,json,hashlib
from pathlib import Path
from unittest.mock import patch
import studio,gateway_profiles as gp,switch,codex_switch

class StudioTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.patches=[patch.object(studio,'BASE',self.root/'.claude'),patch.object(studio,'WORK',self.root/'market'),patch.object(switch,'STATE_ROOT',self.root/'state')]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in self.patches:p.stop()
  self.tmp.cleanup()
 def test_agent_source_and_conflict(self):
  text='---\nname: old\ndescription: Review code\nunknownField: [one, two]\n---\n\n**Bold** and <u>underline</u>\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n'
  v=studio.handle({'op':'save','kind':'agents','name':'reviewer','text':text});path=Path(v['path'])
  self.assertIn('unknownField: [one, two]',path.read_text());self.assertIn('name: "reviewer"',path.read_text());self.assertIn('| 1 | 2 |',path.read_text())
  with self.assertRaises(ValueError):studio.handle({'op':'save','kind':'agents','name':'reviewer','text':text})
 def test_hooks_preserve_settings(self):
  path=studio.BASE/'settings.json';path.parent.mkdir();path.write_text('{"env":{"KEEP":"yes"}}')
  studio.handle({'op':'hook-save','event':'PostToolUse','type':'http','value':'https://example.com/hooks','matcher':'Write'})
  self.assertEqual(json.loads(path.read_text())['env'],{'KEEP':'yes'})
  self.assertEqual(json.loads(path.read_text())['hooks']['PostToolUse'][0]['hooks'][0]['type'],'http')
 def test_plugin_layout_and_components(self):
  v=studio.handle({'op':'plugin-create','name':'test-tools','description':'Tools'})
  root=Path(v['path']);self.assertTrue((root/'.claude-plugin/plugin.json').is_file());self.assertTrue((studio.WORK/'.claude-plugin/marketplace.json').is_file())
  studio.handle({'op':'save','kind':'skills','name':'review','scope':'plugin','pluginPath':str(root),'text':'---\nname: review\ndescription: Review code\n---\nReview $ARGUMENTS.\n'})
  self.assertTrue((root/'skills/review/SKILL.md').is_file())
  self.assertTrue(any(x['scope']=='Draft: test-tools' for x in studio.inventory()['records']))
 def test_no_path_traversal(self):
  with self.assertRaises(ValueError):studio.handle({'op':'save','kind':'agents','name':'../../escape','text':'x'})
 def test_profiles_store_references(self):
  with patch.object(gp,'ROOT',self.root/'state'),patch.object(gp,'FILE',self.root/'state/profiles.json'):
   gp.handle({'op':'profile-save','name':'Local LiteLLM','kind':'LiteLLM','claudeUrl':'http://localhost:4000','codexUrl':'http://localhost:4000/v1','auth':'environment','env':'GATEWAY_API_KEY'})
   self.assertEqual(gp.selected()['env'],'GATEWAY_API_KEY');self.assertTrue(Path(gp.helper()).is_file())
   with self.assertRaises(ValueError):gp.handle({'op':'profile-save','name':'x','claudeUrl':'http://evil.example','codexUrl':'https://example.com','auth':'environment','env':'KEY'})

if __name__=='__main__':unittest.main()

class GatewayRoutingTest(unittest.TestCase):
 def test_custom_desktop_preserves_connectors_and_restores_auth(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);state=root/'state';state.mkdir()
   files={name:root/(name+'.json') for name in ['code','desktop','meta','profile']}
   profile={'inferenceGatewayBaseUrl':'https://original.example/claude','inferenceProvider':'gateway','inferenceCredentialKind':'oidc','inferenceIdpOidc':{'clientId':'public-client-id'},'managedMcpServers':[{'name':'keep-me'}]}
   files['code'].write_text('{}');files['desktop'].write_text('{"deploymentMode":"1p"}');files['meta'].write_text(json.dumps({'entries':[{'id':switch.GATEWAY_PROFILE_ID}]}));files['profile'].write_text(json.dumps(profile))
   helper=root/'helper.sh';helper.write_text('#!/bin/sh\nexit 0\n');helper.chmod(0o700)
   custom={'id':'custom','name':'My gateway','claudeUrl':'https://custom.example/anthropic','helper':str(helper),'auth':'helper'}
   patches=[patch.object(switch,'CODE_SETTINGS',files['code']),patch.object(switch,'DESKTOP_SETTINGS',files['desktop']),patch.object(switch,'PROFILE_META',files['meta']),patch.object(switch,'GATEWAY_PROFILE',files['profile']),patch.object(switch,'ZSHRC',root/'zshrc'),patch.object(switch,'STATE_ROOT',state),patch.object(switch,'HELPER',helper),patch.object(switch,'ACTIVE_GATEWAY',custom),patch.object(switch,'GATEWAY_URL',custom['claudeUrl']),patch.object(gp,'load',return_value={'profiles':[custom]})]
   for p in patches:p.start()
   try:
    switch.apply(True,True);saved=json.loads(files['profile'].read_text());self.assertEqual(saved['inferenceCredentialHelper'],str(helper));self.assertEqual(saved['managedMcpServers'],profile['managedMcpServers'])
    switch.ACTIVE_GATEWAY={'id':'existing','name':'Original'};switch.GATEWAY_URL='https://original.example/claude'
    switch.apply(True,False);restored=json.loads(files['profile'].read_text());self.assertEqual(restored['inferenceIdpOidc'],profile['inferenceIdpOidc']);self.assertNotIn('inferenceCredentialHelper',restored)
   finally:
    for p in patches:p.stop()
 def test_failed_combined_apply_restores_client_files(self):
  import apply_bundle
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);paths=[root/str(i) for i in range(7)]
   for p in paths:p.write_text('original')
   names=['CODE_SETTINGS','DESKTOP_SETTINGS','PROFILE_META','GATEWAY_PROFILE','ZSHRC'];patches=[patch.object(switch,k,v) for k,v in zip(names,paths[:5])]+[patch.object(codex_switch,'CONFIG',paths[5]),patch.object(codex_switch,'STATE',paths[6]),patch.object(switch,'STATE_ROOT',root)]
   for p in patches:p.start()
   def route(*args):paths[0].write_text('modified');return {}
   try:
    with patch.object(switch,'apply',side_effect=route),patch.object(codex_switch,'status',return_value={'codex_gateway':False}),patch.object(codex_switch,'apply',side_effect=ValueError('failed')):
     with self.assertRaises(ValueError):apply_bundle.apply(True,True,True,'model')
    self.assertTrue(all(p.read_text()=='original' for p in paths))
   finally:
    for p in patches:p.stop()
