/* globals describe, expect, it, jest, WebSocket */
import WorkflowWebsocket from './WorkflowWebsocket'
import { tick } from './test-utils'

/**
 * A fake Websocket.
 *
 * Usage:
 *
 *     const socket = new MockSocket()
 *     socket.onopen = (ev) => { ... }
 *     socket.onmessage = (ev) => { ... }
 *     socket.onclose = (ev) => { ... }
 *     socket.onerror = (ev) => { ... }
 *     setTimeout(() => {
 *         // At this point, onOpen() will have been called.
 *     }, 0)
 */
class MockSocket {
  constructor () {
    this.sends = []
    this.readyState = WebSocket.CONNECTING
    setTimeout(() => {
      this.readyState = WebSocket.OPEN
      this.onopen({})
    }, 0)
  }

  // Caller should overwrite these methods
  onopen (ev) {}

  onclose (ev) {}

  onmessage (ev) {}

  onerror (ev) {}

  send (data) { this.sends.push(data) }
}

describe('WorkflowWebsocket', () => {
  it('should connect', async () => {
    const api = new WorkflowWebsocket(1, jest.fn(), () => new MockSocket())
    api.connect()
    await tick()
    expect(api.socket).toBeDefined()
  })

  it('should reconnect on close and reload workflow again', async () => {
    const spy = jest.spyOn(global.console, 'log').mockImplementation(() => {})
    try {
      const api = new WorkflowWebsocket(1, jest.fn(), () => new MockSocket())
      const socket1 = api.socket
      api.reconnectDelay = 0
      api.connect()
      await tick()
      api.onClose({})
      await tick() // create new socket
      await tick() // have it call onopen
      expect(spy).toHaveBeenCalledWith('Websocket reconnected')
      expect(api.socket).not.toBe(socket1)
    } finally {
      spy.mockRestore()
    }
  })

  it('should callServerHandler() and  await successful response', async () => {
    const socket = new MockSocket()
    await tick() // so socket setTimeout finishes
    const api = new WorkflowWebsocket(1, jest.fn(), () => socket)
    api.connect() // set api.socket
    const future = api.callServerHandler('foo.bar', { x: 'y' })
    expect(socket.sends.map(JSON.parse)).toEqual([{ requestId: 1, path: 'foo.bar', arguments: { x: 'y' } }])
    socket.onmessage({ data: JSON.stringify({ response: { requestId: 1, data: 'ok' } }) })
    const data = await future
    expect(data).toEqual('ok')
  })

  it('should callServerHandler() and  await error response', async () => {
    const socket = new MockSocket()
    await tick() // so socket setTimeout finishes
    const api = new WorkflowWebsocket(1, jest.fn(), () => socket)
    api.connect() // set api.socket
    const future = api.callServerHandler('foo/bar', { x: 'y' })
    expect(socket.sends.map(JSON.parse)).toEqual([{ requestId: 1, path: 'foo/bar', arguments: { x: 'y' } }])
    socket.onmessage({ data: JSON.stringify({ response: { requestId: 1, error: 'bad' } }) })
    let err = null
    try {
      await future // can't expect(() => await future).toThrow() because await is in a sync function there
    } catch (e) {
      err = e
    }
    expect(err).toBeDefined()
    expect(err.message).toEqual('Server reported a problem')
    expect(err.serverError).toEqual('bad')
  })

  it('should queue callServerHandler() when sent before connect starts', async () => {
    let socket
    const buildSocket = () => { socket = new MockSocket(); return socket }
    const api = new WorkflowWebsocket(1, jest.fn(), buildSocket)
    const future = api.callServerHandler('foo.bar', { x: 'y' })
    api.connect()
    expect(socket.sends.length).toEqual(0) // not connected yet
    await tick()
    expect(socket.sends.map(JSON.parse)).toEqual([{ requestId: 1, path: 'foo.bar', arguments: { x: 'y' } }])
    socket.onmessage({ data: JSON.stringify({ response: { requestId: 1, data: 'ok' } }) })
    const data = await future
    expect(data).toEqual('ok')
  })

  it('should queue callServerHandler() when sent before connect completes', async () => {
    let socket
    const buildSocket = () => { socket = new MockSocket(); return socket }
    const api = new WorkflowWebsocket(1, jest.fn(), buildSocket)
    api.connect()
    const future = api.callServerHandler('foo.bar', { x: 'y' }) // onopen not called yet
    expect(socket.sends.length).toEqual(0) // not connected yet
    await tick()
    expect(socket.sends.map(JSON.parse)).toEqual([{ requestId: 1, path: 'foo.bar', arguments: { x: 'y' } }])
    socket.onmessage({ data: JSON.stringify({ response: { requestId: 1, data: 'ok' } }) })
    const data = await future
    expect(data).toEqual('ok')
  })

  it('should handle async requests from server', async () => {
    const socket = new MockSocket()
    await tick() // so socket setTimeout finishes
    const onDelta = jest.fn()
    const api = new WorkflowWebsocket(1, onDelta, () => socket)
    api.connect() // set api.socket

    socket.onmessage({ data: JSON.stringify({ type: 'apply-delta', data: 'data' }) })
    expect(onDelta).toHaveBeenCalled()
  })
})
