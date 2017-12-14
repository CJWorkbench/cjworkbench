# Websocket connection routing, and background proceses.

from channels.routing import route
from server.websockets import ws_add, ws_disconnect
from server.execute import execute_render_message_consumer

channel_routing = [
    route("websocket.connect", ws_add),
    route("websocket.disconnect", ws_disconnect),
    route('execute-render', execute_render_message_consumer),
]

