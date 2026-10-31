"""Common entities and devices."""
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN
from .mapping import extract

DEVICES={
 'router':('Домашний интернет','OpenWrt / MikroTik'),
 'gpon':('Оптический канал','Huawei MA5671A'),
 'cellular':('Резервный 4G','Keenetic / LTE'),
}
class FailoverEntity(CoordinatorEntity):
    _attr_has_entity_name=True
    def __init__(self, coordinator, key, device):
        super().__init__(coordinator)
        self.key=key
        self._attr_translation_key=key
        self._attr_unique_id=f'{coordinator.config_entry.entry_id}_{key}'
        name,model=DEVICES[device]
        self._attr_device_info=DeviceInfo(identifiers={(DOMAIN,coordinator.config_entry.entry_id+'_'+device)},name=name,manufacturer='Домашняя сеть',model=model,via_device=(DOMAIN,coordinator.config_entry.entry_id+'_router') if device!='router' else None)
    @property
    def value(self):
        return extract(self.coordinator.data or {}).get(self.key)
    @property
    def available(self):
        return super().available and self.value is not None
