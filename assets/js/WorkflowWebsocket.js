/* globals WebSocket */
const MissingInflightHandler = {
  resolve: result => {
    console.warn('Unhandled result from server', result)
  },

  reject: result => {
    console.error('Unhandled reror from server', result)
  }
}

export class ErrorResponse extends Error {
  name = 'ErrorResponse'

  constructor (serverError) {
    super('Server reported a problem')
    this.serverError = serverError
  }
}

export default class WorkflowWebsocket {
  constructor (workflowIdOrSecretId, onDelta, createSocket = null) {
    if (!createSocket) {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const url = `${protocol}//${window.location.host}/workflows/${workflowIdOrSecretId}`
      createSocket = () => {
        return new window.WebSocket(url)
      }
    }

    this.queuedMessages = []

    this.workflowIdOrSecretId = workflowIdOrSecretId
    this.onDelta = onDelta
    this.createSocket = createSocket
    this.hasConnectedBefore = false
    this.reconnectDelay = 1000
    this.lastRequestId = 0

    this.inflight = {} // { [requestId]: {resolve, reject} callbacks }
  }

  onOpen = ev => {
    if (this.hasConnectedBefore) {
      console.log('Websocket reconnected')
    } else {
      this.hasConnectedBefore = true
    }

    for (const message of this.queuedMessages) {
      this.socket.send(message)
    }
    this.queuedMessages.splice(0, this.queuedMessages.length)
  }

  onMessage = ev => {
    const data = JSON.parse(ev.data)

    if (data.response) {
      const response = data.response

      const requestId = response.requestId
      const inflight = this.inflight[requestId] || MissingInflightHandler
      delete this.inflight[requestId]

      if (response.error) {
        inflight.reject(new ErrorResponse(response.error))
      } else {
        inflight.resolve(response.data)
      }
    } else if (data.type) {
      switch (data.type) {
        case 'apply-delta':
          this.onDelta(data.data)
          break
        default:
          console.error('Unhandled websocket message', data)
      }
    }
  }

  onError = ev => {
    // ignore: errors during connection are usually logged by browsers anyway;
    // other errors will cause onClose, leading to reconnect.
  }

  onClose = ev => {
    console.log(`Websocket closed. Reconnecting in ${this.reconnectDelay}ms`)
    setTimeout(this.connect, this.reconnectDelay)
  }

  connect = () => {
    this.socket = this.createSocket()
    this.socket.onopen = this.onOpen
    this.socket.onmessage = this.onMessage
    this.socket.onclose = this.onClose
    this.socket.onerror = this.onError
  }

  /**
   * Send data to server (WebSocket.send), _or_ enqueue it if not connected.
   *
   * WorkflowWebsocket guarantees at-least-once delivery: it does not retry
   * failed messages. It does handle page init nicely by waiting for the page
   * to load before sending the first messages.
   */
  _sendOrQueue = message => {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(message)
    } else {
      this.queuedMessages.push(message)
    }
  }

  /**
   * Call a method on the server; return a Promise of its result.
   *
   * The Promise will be rejected if the server sends something that looks like
   * { "result": { "error": "Some error message" } }.
   *
   * Messages are sent in the order they're queued; they're _processed_ in the
   * order the _servers_ decide (which may be different). Each message is
   * augmented with a "requestId" property; the server must echo that
   * "requestId" in its response.
   *
   * TODO add a timeout
   */
  callServerHandler (path, args) {
    const requestId = ++this.lastRequestId
    const message = JSON.stringify({ path, requestId, arguments: args })

    this._sendOrQueue(message)

    return new Promise((resolve, reject) => {
      this.inflight[requestId] = { resolve, reject }
    })
  }
}
