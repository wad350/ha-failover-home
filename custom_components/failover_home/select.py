"""Explicit user control of WAN mode; reads never change routing."""
from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError
from .const import DOMAIN
from .entity import FailoverEntity
from .api import FailoverError

async def async_setup_entry(hass,entry,async_add_entities):
    async_add_entities([FailoverMode(hass.data[DOMAIN][entry.entry_id])])
class FailoverMode(FailoverEntity,SelectEntity):
    _attr_options=['auto','pppoe','4g']
    _attr_icon='mdi:swap-horizontal'
    def __init__(self,co): super().__init__(co,'mode','router')
    @property
    def current_option(self): return self.value
    async def async_select_option(self,option):
        if option not in self.options: raise HomeAssistantError('Неизвестный режим')
        try:
            await self.coordinator.client.call('mode',{'mode':option})
            await self.coordinator.async_request_refresh()
        except FailoverError as exc:
            raise HomeAssistantError(str(exc)) from exc
