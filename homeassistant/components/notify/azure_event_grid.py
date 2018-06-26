"""
Azure Event Grid platform for notify component.

For more details about this platform, please refer to the documentation at
TBD

Created by Eduard van Valkenburg
"""

import logging
import json
import base64
import voluptuous as vol
from datetime import datetime
import pytz
import uuid

from homeassistant.const import (CONF_HOST, CONF_PLATFORM, CONF_NAME)
<<<<<<< HEAD
from homeassistant.components.notify import (ATTR_DATA, PLATFORM_SCHEMA, BaseNotificationService)
=======
from homeassistant.components.notify import (ATTR_DATA, ATTR_TITLE, ATTR_TITLE_DEFAULT, PLATFORM_SCHEMA, BaseNotificationService)
>>>>>>> c19b9bc... added v1 of azure_event_grid
import homeassistant.helpers.config_validation as cv
from homeassistant.remote import JSONEncoder

REQUIREMENTS = ['azure.eventgrid==0.1.0', 'msrest==0.4.29']

_LOGGER = logging.getLogger(__name__)

CONF_TOPIC_KEY = 'topic key'
<<<<<<< HEAD
CONF_SUBJECT = 'subject'
CONF_EVENT_TYPE = 'eventtype'
CONF_EVENT_TYPE_DEFAULT = 'HomeAssistant'
CONF_DATA_VERSION = 'dataversion'
CONF_DATA_VERSION_DEFAULT = 1

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Inclusive(CONF_TOPIC_KEY,'authentication'): cv.string
=======
CONF_CONTEXT = 'context'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_TOPIC_KEY): cv.string,
    vol.Optional(CONF_CONTEXT, default=dict()): vol.Coerce(dict)
>>>>>>> c19b9bc... added v1 of azure_event_grid
})

def get_service(hass, config, discovery_info=None):
    from azure.eventgrid import EventGridClient
    from msrest.authentication import TopicCredentials

<<<<<<< HEAD
    credentials = TopicCredentials(config[CONF_TOPIC_KEY])
    event_grid_client = EventGridClient(credentials)

    return AzureEventGrid(config[CONF_HOST], event_grid_client)
=======
    #create the context dict, puts the HASS config in there as well as a custom piece if configured.
    context = {
        'hass': json.loads(json.dumps(hass.config.as_dict(), cls=JSONEncoder)),
        'custom': config[CONF_CONTEXT]
        }
    #create credentials from the key, and create the event_grid_client with the creds.
    credentials = TopicCredentials(config[CONF_TOPIC_KEY])
    event_grid_client = EventGridClient(credentials)

    return AzureEventGrid(config[CONF_HOST], event_grid_client, context)
>>>>>>> c19b9bc... added v1 of azure_event_grid

class AzureEventGrid(BaseNotificationService):
    """Implement the notification service for the azure event grid."""

<<<<<<< HEAD
    def __init__(self, endpoint, event_grid_client):
        """Initialize the service."""
        self.endpoint = endpoint
        self.client = event_grid_client

    def send_message(self, message="", **kwargs):
        data = kwargs.get(ATTR_DATA)
        subject = data.get(CONF_SUBJECT)
        eventType = data.get(CONF_EVENT_TYPE, CONF_EVENT_TYPE_DEFAULT)
        dataVersion = data.get(CONF_DATA_VERSION, CONF_DATA_VERSION_DEFAULT)

        #create the payload, with subject, data and type coming in from the notify platform
        payload = {
            'id' : str(uuid.uuid4()),
            'subject': subject,
            'data': message,
            'event_type': eventType,
            'event_time': datetime.utcnow().replace(tzinfo=pytz.UTC),
            'data_version': dataVersion
=======
    def __init__(self, endpoint, event_grid_client, context):
        """Initialize the service."""
        self.endpoint = endpoint
        self.client = event_grid_client
        self.context = context

    def send_message(self, message="", **kwargs):
        title = kwargs.get(ATTR_TITLE, ATTR_TITLE_DEFAULT)
        data = kwargs.get(ATTR_DATA)

        #create the payload, with Title, Message and Data coming in from the notify platform
        payload = {
            'id' : str(uuid.uuid4()),
            'subject': title,
            'data': {
                'message': message,
                'data': data,
                'context': self.context
            },
            'event_type': 'HassEventType',
            'event_time': datetime.utcnow().replace(tzinfo=pytz.UTC),
            'data_version': 1
>>>>>>> c19b9bc... added v1 of azure_event_grid
        }

        #Send the event to event grid
        try:
            self.client.publish_events(
                self.endpoint,
                events=[payload]
            )
<<<<<<< HEAD
        except HomeAssistantError as err:
            _LOGGER.error("Unable to send event to Event Grid: %s", err)
=======
        except:
            _LOGGER.error("Unable to send event to Event Grid")
>>>>>>> c19b9bc... added v1 of azure_event_grid
