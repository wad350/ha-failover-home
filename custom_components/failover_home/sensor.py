"""Failover sensors."""
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature, UnitOfDataRate
from .const import DOMAIN
from .entity import FailoverEntity

# key, device, unit, device class, options, icon
SENSORS = [
 ('active_channel','router',None,'enum',['pppoe','4g','offline'],'mdi:wan'),
 ('primary_ip','gpon',None,None,None,'mdi:ip-network'),('backup_ip','cellular',None,None,None,'mdi:ip-network'),
 ('operator','cellular',None,None,None,'mdi:cellphone'),('radio','cellular',None,'enum',['4g','4g_plus'],'mdi:signal'),('bands','cellular',None,None,None,'mdi:signal-cellular-3'),
 ('rsrp','cellular','dBm','signal_strength',None,'mdi:signal'),('rssi','cellular','dBm','signal_strength',None,'mdi:signal'),('rsrq','cellular','dB',None,None,'mdi:signal'),('sinr','cellular','dB',None,None,'mdi:signal'),
 ('modem_temperature','cellular','°C','temperature',None,'mdi:thermometer'),('cellular_cpu_temperature','cellular','°C','temperature',None,'mdi:thermometer'),
 ('sfp_rx','gpon','dBm',None,None,'mdi:arrow-down'),('sfp_tx','gpon','dBm',None,None,'mdi:arrow-up'),
 ('sfp_temperature','gpon','°C','temperature',None,'mdi:thermometer'),('sfp_cpu_temperature','gpon','°C','temperature',None,'mdi:thermometer'),('board_temperature','router','°C','temperature',None,'mdi:thermometer'),
 ('restriction_state','cellular',None,'enum',['enabled','disabled','unreachable'],'mdi:shield-alert'),('vpn_state','cellular',None,'enum',['up','off','checking'],'mdi:vpn'),
 ('primary_download','gpon','bit/s','data_rate',None,'mdi:download'),('primary_upload','gpon','bit/s','data_rate',None,'mdi:upload'),('backup_download','cellular','bit/s','data_rate',None,'mdi:download'),('backup_upload','cellular','bit/s','data_rate',None,'mdi:upload'),
]
async def async_setup_entry(hass,entry,async_add_entities):
    co=hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FailoverSensor(co,*row) for row in SENSORS])

class FailoverSensor(FailoverEntity,SensorEntity):
    def __init__(self,co,key,device,unit,device_class,options,icon):
        super().__init__(co,key,device)
        self._attr_native_unit_of_measurement=unit
        self._attr_device_class=SensorDeviceClass(device_class) if device_class else None
        self._attr_options=options
        self._attr_icon=icon
        if unit is not None: self._attr_state_class=SensorStateClass.MEASUREMENT
    @property
    def native_value(self): return self.value
    @property
    def extra_state_attributes(self):
        if self.key != 'backup_ip': return None
        cell=(self.coordinator.data or {}).get('cellular') or {}
        if cell.get('manager_error'): return None
        vpn=(cell.get('whitelist') or {}).get('vpn_on')
        return {'vpn_active': vpn} if isinstance(vpn,bool) else None
