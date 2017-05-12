# Receive and send websockets messages.
# Clients open a socket on a specific workflow, and all clients viewing that workflow are a "group"
import json
from channels import Group
from server.models import Workflow

# Clients connect to channels at ws://server/workflows/[id]
# This extracts the id. Throws ValueError if id is not an int
def ws_url_to_id(url):
    id = url.rstrip('/').split('/')[-1]
    return int(id)

# Convert workflow id to channel group name
def ws_id_to_group(id):
    return "workflow-"+str(id)

# Client connects to URL to start monitoring for changes
def ws_add(message):
    id =  ws_url_to_id(message.content['path'])
    try:
        workflow = Workflow.objects.get(pk=id)
    except Workflow.DoesNotExist:
        message.reply_channel.send({'accept': False})       # can't find that workflow, don't connect
        return

    Group(ws_id_to_group(id)).add(message.reply_channel)
    message.reply_channel.send({'accept': True})


# Remove from workflow->channel dict when client disconnects
def ws_disconnect(message):
    id =  ws_url_to_id(message.content['path'])
    Group(ws_id_to_group(id)).discard(message.reply_channel)


# Send a message to all clients listening to a workflow
def ws_send_workflow_update(workflow, message_dict):
    # print("Sending message to " + str(workflow.id) + ": " + str(message_dict))
    Group(ws_id_to_group(workflow.id)).send({'text' : json.dumps(message_dict)}, immediately=True)

# Tell clients to reload entire workflow
def ws_client_rerender_workflow(workflow):
    message = { 'type': 'reload-workflow'}
    ws_send_workflow_update(workflow, message)

# Tell clients to reload specific wfmodule
def ws_client_wf_module_status(wf_module, status):
    workflow = wf_module.workflow
    message = { 'type' : 'wfmodule-status', 'id' : wf_module.id, 'status' : status}
    ws_send_workflow_update(workflow, message)


