# Websocket connection routing. Just send everything to our server.

from channels.routing import route
from server.websockets import ws_add, ws_disconnect

channel_routing = [
    route("websocket.connect", ws_add),
    route("websocket.disconnect", ws_disconnect),
]

