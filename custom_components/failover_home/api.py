"""Authenticated LuCI ubus client with pinned TLS certificate."""
from __future__ import annotations
import asyncio
import re
from urllib.parse import urlsplit
import aiohttp

class FailoverError(Exception):
    """Communication or authentication error; never includes credentials."""

class FailoverAuthError(FailoverError):
    """Credentials or session rejected."""


def normalize_config(url: str, fingerprint: str) -> tuple[str, bytes]:
    try:
        p = urlsplit(url.strip().rstrip('/'))
    except (ValueError, AttributeError) as ex:
        raise ValueError('invalid_url') from ex
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.path not in ('', '/') or p.query or p.fragment:
        raise ValueError('invalid_url')
    raw = re.sub(r'[:\s]', '', fingerprint)
    if not re.fullmatch(r'[0-9a-fA-F]{64}', raw):
        raise ValueError('invalid_fingerprint')
    return p.geturl().rstrip('/'), bytes.fromhex(raw)

class FailoverClient:
    def __init__(self, session: aiohttp.ClientSession, url: str, username: str, password: str, fingerprint: str):
        self._session = session
        self._url, raw = normalize_config(url, fingerprint)
        self._pin = aiohttp.Fingerprint(raw)
        self._username, self._password = username, password
        self._sid = None
        self._lock = asyncio.Lock()

    async def _raw(self, sid, obj, method, arguments):
        body = {'jsonrpc':'2.0','id':1,'method':'call','params':[sid,obj,method,arguments]}
        try:
            async with self._session.post(self._url+'/ubus', json=body, ssl=self._pin, timeout=aiohttp.ClientTimeout(total=25)) as response:
                if response.status in (401, 403):
                    raise FailoverAuthError('Доступ к OpenWrt запрещён')
                if response.status != 200:
                    raise FailoverError(f'OpenWrt HTTP {response.status}')
                data = await response.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as ex:
            raise FailoverError('OpenWrt недоступен или сертификат изменился') from ex
        if not isinstance(data, dict):
            raise FailoverError('Некорректный ответ OpenWrt')
        if isinstance(data.get('error'), dict):
            if data['error'].get('code') == -32002:
                raise FailoverAuthError('Сессия OpenWrt недействительна')
            raise FailoverError('Ошибка JSON-RPC OpenWrt')
        if not isinstance(data.get('result'), list) or not data['result']:
            raise FailoverError('Некорректный ответ OpenWrt')
        result=data['result']
        if result[0] == 6:
            raise FailoverAuthError('Сессия OpenWrt недействительна')
        if result[0] != 0 or len(result) < 2 or not isinstance(result[1],dict):
            raise FailoverError('Ошибка вызова OpenWrt')
        result=result[1]
        if result.get('login_required'):
            raise FailoverAuthError('Необходим вход в роутер')
        if result.get('error'):
            if 'Требуется вход' in str(result['error']):
                raise FailoverAuthError('Сессия OpenWrt недействительна')
            safe_mode_errors = {'PPPoE сейчас не подключён. Дождитесь восстановления соединения', 'На ether5 нет адреса DHCP от Keenetic', 'Keenetic не отвечает. Режим не изменён', 'На MikroTik отсутствует переключатель каналов', 'Другое изменение уже выполняется'}
            if method == 'mode' and isinstance(result['error'], str) and result['error'] in safe_mode_errors:
                raise FailoverError(result['error'])
            raise FailoverError('Ошибка получения данных роутера')
        return result

    async def _login(self):
        result=await self._raw('0'*32,'session','login',{'username':self._username,'password':self._password})
        sid=result.get('ubus_rpc_session')
        if not isinstance(sid,str) or not re.fullmatch('[0-9a-f]{32}',sid) or sid=='0'*32:
            raise FailoverAuthError('Не удалось войти в OpenWrt')
        self._sid=sid

    async def call(self, method: str, args: dict | None = None):
        # Serialize login and calls to avoid simultaneous session renewal or session-cache races.
        async with self._lock:
            if not self._sid:
                await self._login()
            for attempt in range(2):
                try:
                    return await self._raw(self._sid,'mikrotik-dashboard',method,args or {})
                except FailoverAuthError:
                    self._sid=None
                    if attempt:
                        raise
                    await self._login()

    async def snapshot(self):
        result={}
        failures=[]
        for name in ('status','cellular','traffic'):
            try:
                result[name]=await self.call(name)
            except FailoverAuthError:
                raise
            except FailoverError as exc:
                result[name]=None
                failures.append(exc)
        if len(failures)==3:
            raise FailoverError('Нет данных Failover') from failures[0]
        return result
