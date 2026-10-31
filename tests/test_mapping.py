import unittest
from datetime import datetime,timezone,timedelta
from custom_components.failover_home.mapping import extract, restriction_state

class MappingTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime.now(timezone.utc)
        self.cell={'whitelist':{'checked_once':True,'checked':self.now.isoformat(),'open_ok':False,'whitelist_ok':True,'vpn_on':True,'vpn_ready':True,'vpn_healthy':True},'signal':{'rsrp':'-77','rssi':'-46','rsrq':'-11','connected':True,'carriers':[{'band':'7','bandwidth':'20'},{'band':'3'}]},'temperature':{'sensors':[{'name':'PA','value':0}]}}
        self.status={'current':'pppoe','mode':'auto','primary':{'connected':True,'probes':[{'address':'probe-a','enabled':True,'reachable':True},{'address':'probe-b','enabled':False,'reachable':None}]},'backup':{'ready':False},'sfp':{'rx':'-23.4','gpon':{'rx':None,'state':5,'signal':True}},'device':{'health':{'temperatures':[{'name':'temperature','value':44}]}}}
        self.traffic={'age':2,'history':{'pppoe':[{'age_ms':2000,'rx':0,'tx':120}]}}
    def test_current_and_zero(self):
        m=extract({'status':self.status,'cellular':self.cell,'traffic':self.traffic},self.now)
        self.assertEqual((m['active_channel'],m['radio'],m['rsrp']),('pppoe','4g_plus',-77))
        self.assertEqual((m['modem_temperature'],m['primary_download'],m['primary_upload']),(0,0,120))
        self.assertEqual((m['probe_one'],m['probe_two'],m['backup_gateway']),(True,None,False))
        self.assertEqual((m['sfp_rx'],m['gpon_registered'],m['restriction_active'],m['vpn_state']),(-23.4,True,True,'up'))
    def test_unavailable_data_never_asserts_recovery(self):
        self.cell['whitelist']['checked']=(self.now-timedelta(seconds=181)).isoformat()
        self.cell['signal']['connected']=False
        self.traffic['age']=16
        m=extract({'status':self.status,'cellular':self.cell,'traffic':self.traffic},self.now)
        self.assertIsNone(m['restriction_active']);self.assertIsNone(m['radio']);self.assertIsNone(m['primary_download'])
        self.cell['manager_error']='bad';self.cell['signal_error']='bad'
        m=extract({'status':None,'cellular':self.cell,'traffic':None},self.now)
        for k in ['active_channel','backup_gateway','rsrp','restriction_active','bypass_enabled','primary_download']:
            self.assertIsNone(m[k],k)
    def test_both_probes_down_is_unknown_whitelist(self):
        self.cell['whitelist']['whitelist_ok']=False
        m=extract({'cellular':self.cell},self.now)
        self.assertEqual(m['restriction_state'],'unreachable');self.assertIsNone(m['restriction_active'])
        self.cell['whitelist']['open_ok']=True
        self.assertFalse(extract({'cellular':self.cell},self.now)['restriction_active'])
    def test_missing_invalid_data(self):
        self.assertTrue(all(v is None for v in extract({}).values()))
        self.cell['whitelist']['checked']='not a date'
        self.assertIsNone(restriction_state(self.cell,self.now))
        self.cell['whitelist']['checked']=(self.now+timedelta(seconds=31)).isoformat()
        self.assertIsNone(restriction_state(self.cell,self.now))

if __name__=='__main__': unittest.main()
