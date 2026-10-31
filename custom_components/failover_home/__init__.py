"""Home Assistant integration for the home OpenWrt failover dashboard."""
from __future__ import annotations
from datetime import timedelta
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import FailoverClient, FailoverError, FailoverAuthError
from .const import DOMAIN, PLATFORMS

class FailoverCoordinator(DataUpdateCoordinator):
    def __init__(self,hass,entry,client):
        super().__init__(hass,logger=logging.getLogger(__name__),name=DOMAIN,config_entry=entry,update_interval=timedelta(seconds=30))
        self.client=client
    async def _async_update_data(self):
        try:
            return await self.client.snapshot()
        except FailoverAuthError as exc:
            from homeassistant.exceptions import ConfigEntryAuthFailed
            raise ConfigEntryAuthFailed('Вход в OpenWrt отклонён') from exc
        except FailoverError as exc:
            raise UpdateFailed(str(exc)) from exc

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client=FailoverClient(async_get_clientsession(hass),entry.data[CONF_HOST],entry.data[CONF_USERNAME],entry.data[CONF_PASSWORD],entry.data['fingerprint'])
    coordinator=FailoverCoordinator(hass,entry,client)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN,{})[entry.entry_id]=coordinator
    await hass.config_entries.async_forward_entry_setups(entry,PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if await hass.config_entries.async_unload_platforms(entry,PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id,None)
        return True
    return False
