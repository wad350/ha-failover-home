import asyncio,unittest
import aiohttp
from custom_components.failover_home.api import FailoverClient,FailoverAuthError,FailoverError,normalize_config

PIN='aa'*32
class Response:
    status=200
    def __init__(self,body): self.body=body
    async def __aenter__(self): return self
    async def __aexit__(self,*args): pass
    async def json(self,**kwargs): return self.body
class Session:
    def __init__(self,answers): self.answers=list(answers);self.calls=[]
    def post(self,url,**kw):
        assert isinstance(kw['ssl'],aiohttp.Fingerprint)
        assert 'ubus_rpc_session' not in kw['json']['params'][3]
        self.calls.append((url,kw['json']['params'][1:3]))
        return Response(self.answers.pop(0))
def success(value): return {'jsonrpc':'2.0','result':[0,value]}
def denied(): return {'jsonrpc':'2.0','error':{'code':-32002,'message':'Access denied'}}
class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_expired_session_reauth_once(self):
        session=Session([success({'ubus_rpc_session':'a'*32}),denied(),success({'ubus_rpc_session':'b'*32}),success({'ok':True})])
        client=FailoverClient(session,'https://router.local','root','fixture',PIN)
        self.assertTrue((await client.call('status'))['ok'])
        self.assertEqual([x[1][1] for x in session.calls],['login','status','login','status'])
    async def test_wrong_password_is_auth_error(self):
        client=FailoverClient(Session([denied()]),'https://router.local','root','fixture',PIN)
        with self.assertRaises(FailoverAuthError): await client.call('status')
    async def test_mode_timeout_must_not_be_retried(self):
        session=Session([success({'ubus_rpc_session':'a'*32}),{'result':[7]}])
        client=FailoverClient(session,'https://router.local','root','fixture',PIN)
        with self.assertRaises(FailoverError): await client.call('mode',{'mode':'auto'})
        self.assertEqual([x[1][1] for x in session.calls],['login','mode'])
    async def test_no_secret_in_exception(self):
        client=FailoverClient(Session([{'error':{'code':-32001,'message':'fixture password'}}]),'https://router.local','root','fixture',PIN)
        with self.assertRaises(FailoverError) as cm: await client.call('status')
        self.assertNotIn('fixture',str(cm.exception))
    async def test_mode_only_once(self):
        session=Session([success({'ubus_rpc_session':'a'*32}),success({'ok':True})])
        client=FailoverClient(session,'https://router.local','root','fixture',PIN)
        await client.call('mode',{'mode':'auto'})
        self.assertEqual([x[1][1] for x in session.calls],['login','mode'])
class ConfigTests(unittest.TestCase):
    def test_pinning_required_and_https(self):
        self.assertEqual(normalize_config('https://router.local','AA:'*31+'AA')[1],bytes.fromhex(PIN))
        for url,pin in [('http://router.local',PIN),('https://x/p',PIN),('https://x','ab'),('https://name:pass@x',PIN)]:
            with self.assertRaises(ValueError): normalize_config(url,pin)
if __name__=='__main__': unittest.main()
