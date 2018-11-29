const MissingInflightHandler = {
  resolve: (result) => {
    console.warn('Unhandled result from server', result)
  },

  reject: (result) => {
    console.error('Unhandled reror from server', result)
  }
}


export default class WorkflowWebsocket {
  constructor(workflowId, store) {
    this.workflowId = workflowId
    this.store = store
    this.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    this.url = `${protocol}//${window.location.host}/workflows/${this.workflowId}`
    this.nSuccessfulOpens = 0
    this.lastRequestId = 0

    this.inflight = {} // { [requestId]: {resolve, reject} callbacks }
  }

  onOpen (ev) {
    this.nSuccessfulOpens += 1
    if (nSuccessfulOpens === 1) {
      this.store.dispatch(Actions.reloadWorkflowAction())
    } else {
      console.log('Websocket reconnected')
    }
  }

  onMessage (ev) {
    const data = JSON.parse(ev.data)

    if ('result' in data) {
      const result = data.result

      let inflight
      if (data.requestId) {
        const requestId = data.requestId
        delete data.requestId

        inflight = this.inflight[requestId] || MissingInflightHandler
        delete this.inflight[requestId]
      } else {
        inflight = MissingInflightHandler
      }

      if (result.error) {
        inflight.reject(result)
      } else {
        inflight.resolve(result)
      }
    } else if ('type' in data) {
      switch (data.type) {
        case 'apply-delta':
          this.store.dispatch(Actions.applyDeltaAction(data.data))
          return
        case 'set-wf-module':
          this.store.dispatch(Actions.setWfModuleAction(data.data))
          return
        case 'set-workflow':
          this.store.dispatch(Actions.setWorkflowAction(data.data))
          return
        case 'reload-workflow':
          this.store.dispatch(Actions.reloadWorkflowAction())
          return
        default:
          console.error('Unhandled websocket message', data)
      }
    }
  }

  onError (ev) {
    // ignore: errors during connection are usually logged by browsers anyway;
    // other errors will cause onClose, leading to reconnect.
  }

  onClose (ev) {
    console.log('Websocket closed. Reconnecting in 1s')
    setTimeout(this.connect, 1000)
  }

  connect = () => {
    this.socket = new window.WebSocket(url)
    this.socket.onopen = this.onOpen
    this.socket.onmessage = this.onMessage
    this.socket.onclose = this.onClose
    this.socket.onerror = this.onError
  }

  /**
   * Call a method on the server and return right away.
   *
   * This is the method we want to be using most of the time: it plays nice
   * with collaborative edits since we rely on the server to broadcast the
   * outcomes to all users.
   */
  callServerHandler (path, args) {
    this.socket.send(JSON.stringify({ path, 'arguments': args }))
  }

  /**
   * Call a method on the server; return a Promise of its result.
   *
   * The Promise will be rejected if the server sends something that looks like
   * { "result": { "error": "Some error message" } }.
   *
   * Messages are sent in the order they're queued; they're _received_ in the
   * order the _servers_ decide (which may be different). Each message is
   * augmented with a "requestId" property; the server must echo that
   * "requestId" in its response.
   *
   * TODO add a timeout
   */
  callServerHandlerAndWait (path, args) {
    this.lastRequestId++
    const requestId = this.lastRequestId
    this.socket.send(JSON.stringify({ path, requestId, 'arguments': args }))
    return new Promise((resolve, reject) => {
      this.inflight[requestId] = { resolve, reject }
    })
  }
}
