"""UI configuration for Failover Home."""
from __future__ import annotations
from urllib.parse import urlsplit
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector
from .api import FailoverClient, FailoverError, FailoverAuthError, normalize_config
from .const import DOMAIN

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION=1
    async def async_step_user(self, user_input=None):
        errors={}
        if user_input is not None:
            try:
                url, pin=normalize_config(user_input[CONF_HOST],user_input['fingerprint'])
                await self.async_set_unique_id(url.lower())
                self._abort_if_unique_id_configured()
                client=FailoverClient(async_get_clientsession(self.hass),url,user_input[CONF_USERNAME],user_input[CONF_PASSWORD],user_input['fingerprint'])
                await client.call('status')
                return self.async_create_entry(title='Домашняя сеть · Failover',data={**user_input,CONF_HOST:url,'fingerprint':pin.hex()})
            except ValueError as ex:
                errors['base']=str(ex)
            except FailoverAuthError:
                errors['base']='invalid_auth'
            except FailoverError:
                errors['base']='cannot_connect'
        schema=vol.Schema({
            vol.Required(CONF_HOST,default=(user_input or {}).get(CONF_HOST,'https://openwrt.local')): str,
            vol.Required(CONF_USERNAME,default=(user_input or {}).get(CONF_USERNAME,'root')): str,
            vol.Required(CONF_PASSWORD): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
            vol.Required('fingerprint',default=(user_input or {}).get('fingerprint','')): str,
        })
        return self.async_show_form(step_id='user',data_schema=schema,errors=errors)

    async def async_step_reauth(self, entry_data):
        """Prompt for renewed credentials when a stored password is rejected."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        return await self._update_existing('reauth_confirm', self._get_reauth_entry(), user_input)

    async def async_step_reconfigure(self, user_input=None):
        """Allow explicit certificate pin or credential changes without removing entities."""
        return await self._update_existing('reconfigure', self._get_reconfigure_entry(), user_input)

    async def _update_existing(self, step, entry, user_input):
        errors={}
        if user_input is not None:
            try:
                _, pin=normalize_config(entry.data[CONF_HOST],user_input['fingerprint'])
                password=user_input.get(CONF_PASSWORD) or entry.data[CONF_PASSWORD]
                client=FailoverClient(async_get_clientsession(self.hass),entry.data[CONF_HOST],user_input[CONF_USERNAME],password,user_input['fingerprint'])
                await client.call('status')
                return self.async_update_reload_and_abort(entry,data_updates={CONF_USERNAME:user_input[CONF_USERNAME], CONF_PASSWORD:password, 'fingerprint':pin.hex()})
            except ValueError as ex:
                errors['base']=str(ex)
            except FailoverAuthError:
                errors['base']='invalid_auth'
            except FailoverError:
                errors['base']='cannot_connect'
        schema=vol.Schema({
            vol.Required(CONF_USERNAME,default=entry.data[CONF_USERNAME]): str,
            vol.Optional(CONF_PASSWORD,default=''): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
            vol.Required('fingerprint',default=entry.data['fingerprint']): str,
        })
        return self.async_show_form(step_id=step,data_schema=schema,errors=errors)
