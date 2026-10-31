"""Failover binary sensors."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import DOMAIN
from .entity import FailoverEntity
BINARY = [
 ('pppoe_connected','gpon','mdi:connection'),('backup_gateway','cellular','mdi:router-wireless'),
 ('probe_one','gpon','mdi:check-network'),('probe_two','gpon','mdi:check-network'),
 ('gpon_registered','gpon','mdi:fiber-optic'),('optical_signal','gpon','mdi:fiber-optic'),
 ('restriction_active','cellular','mdi:shield-alert'),('bypass_enabled','cellular','mdi:shield-check'),('vpn_running','cellular','mdi:vpn'),
]
async def async_setup_entry(hass,entry,async_add_entities):
    co=hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FailoverBinary(co,*row) for row in BINARY])
class FailoverBinary(FailoverEntity,BinarySensorEntity):
    def __init__(self,co,key,device,icon):
        super().__init__(co,key,device); self._attr_icon=icon
    @property
    def is_on(self): return self.value
    @property
    def extra_state_attributes(self):
        if self.key not in ('probe_one','probe_two'): return None
        probes = (((self.coordinator.data or {}).get('status') or {}).get('primary') or {}).get('probes') or []
        index = 0 if self.key == 'probe_one' else 1
        return {'address': probes[index].get('address')} if len(probes) > index and probes[index].get('address') else None
