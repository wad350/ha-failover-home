"""Normalize optional dashboard data without treating missing telemetry as failure."""
from __future__ import annotations
from datetime import datetime, timezone
import math

def number(v):
    if isinstance(v,bool) or v is None: return None
    try:
        n=float(v)
        return n if math.isfinite(n) else None
    except (ValueError,TypeError): return None

def restriction_state(cellular, now=None):
    if not isinstance(cellular,dict) or cellular.get('manager_error'): return None
    w=cellular.get('whitelist') or {}
    if not w.get('checked_once') or not isinstance(w.get('open_ok'),bool) or not isinstance(w.get('whitelist_ok'),bool): return None
    try:
        ts=datetime.fromisoformat(w['checked'].replace('Z','+00:00'))
        if ts.tzinfo is None: return None
        age=((now or datetime.now(timezone.utc))-ts).total_seconds()
        if age < -30 or age > 180: return None
    except (TypeError,ValueError,KeyError,AttributeError): return None
    if w['open_ok']: return 'disabled'
    if w['whitelist_ok']: return 'enabled'
    return 'unreachable'

def extract(data, now=None):
    status=data.get('status') or {}; cell=data.get('cellular') or {}; traffic=data.get('traffic') or {}
    main=status.get('primary') or {}; backup=status.get('backup') or {}; sfp=status.get('sfp') or {}; gpon=sfp.get('gpon') or {}
    signal=cell.get('signal') or {}; white=cell.get('whitelist') or {}; probes=main.get('probes') or []
    if gpon.get('error'): gpon={}
    if cell.get('signal_error'): signal={}
    if cell.get('manager_error'): white={}
    def probe(index):
        p=probes[index] if len(probes)>index else None
        return p.get('reachable') if p and p.get('enabled') is True and isinstance(p.get('reachable'),bool) else None
    def get_bool(obj,key):
        return obj.get(key) if isinstance(obj.get(key),bool) else None
    def sensor(name):
        temp=cell.get('temperature') or {}
        if temp.get('error'): return None
        return next((number(x.get('value')) for x in temp.get('sensors',[]) if x.get('name')==name),None)
    def rate(channel,direction):
        if traffic.get('collection_error') or number(traffic.get('age')) is None or float(traffic['age'])>=15: return None
        items=(traffic.get('history') or {}).get(channel) or []
        if not items: return None
        last=items[-1]
        if number(last.get('age_ms')) is None or float(last['age_ms'])>=15000: return None
        return number(last.get(direction))
    def tempboard():
        h=(status.get('device') or {}).get('health') or {}
        if h.get('error'): return None
        return next((number(t.get('value')) for t in h.get('temperatures',[]) if t.get('name') in ('temperature','pcb-temperature')),None)
    carriers=signal.get('carriers') or []
    rs=restriction_state(cell,now)
    ext=backup.get('external') or {}
    mode=status.get('mode') if status.get('mode') in ('auto','pppoe','4g') else None
    current=status.get('current') if status.get('current') in ('pppoe','4g','offline') else None
    def optical(gkey, skey):
        n=number(gpon.get(gkey))
        return n if n is not None else number(sfp.get(skey))
    registered = (gpon.get('state')==5) if isinstance(gpon.get('state'),(int,float)) and not isinstance(gpon.get('state'),bool) else None
    vpn_on=get_bool(white,'vpn_on'); ready=get_bool(white,'vpn_ready'); healthy=get_bool(white,'vpn_healthy')
    vpn = None if vpn_on is None else ('off' if not vpn_on else ('up' if ready is True and healthy is True else ('checking' if ready is not None and healthy is not None else None)))
    return {
      'active_channel':current,'mode':mode,'primary_ip':main.get('address'),'backup_ip':None if ext.get('error') else ext.get('address'),
      'operator':signal.get('operator'),'radio':('4g_plus' if len(carriers)>1 else '4g') if carriers and signal.get('connected') is not False else None,
      'bands':', '.join('B'+str(c['band'])+(f" · {c['bandwidth']} МГц" if c.get('bandwidth') else '') for c in carriers if c.get('band') is not None) or None,
      'rsrp':number(signal.get('rsrp')),'rssi':number(signal.get('rssi')),'rsrq':number(signal.get('rsrq')),'sinr':number(signal.get('sinr')),
      'modem_temperature':sensor('PA'),'cellular_cpu_temperature':number((cell.get('cpu_temperature') or {}).get('value')),
      'sfp_rx':optical('rx','rx'),'sfp_tx':optical('tx','tx'),
      'sfp_temperature':optical('optic_temperature','temperature'),'sfp_cpu_temperature':number(gpon.get('cpu_temperature')),
      'board_temperature':tempboard(),'restriction_state':rs,'vpn_state':vpn,
      'primary_download':rate('pppoe','rx'),'primary_upload':rate('pppoe','tx'),'backup_download':rate('4g','rx'),'backup_upload':rate('4g','tx'),
      'pppoe_connected':get_bool(main,'connected'),'backup_gateway':get_bool(backup,'ready'),
      'probe_one':probe(0),'probe_two':probe(1),'gpon_registered':registered,'optical_signal':get_bool(gpon,'signal'),
      'restriction_active': None if rs in (None,'unreachable') else rs=='enabled',
      'bypass_enabled':get_bool(white,'bypass_enabled'), 'vpn_running':vpn_on,
    }
