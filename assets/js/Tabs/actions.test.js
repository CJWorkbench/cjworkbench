import { mockStore, tick } from '../test-utils'
import * as actions from './actions'

describe('Tabs.actions', () => {
  describe('setName', () => {
    it('should setName', async () => {
      const api = {
        setTabName: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        tabs: {
          2: { name: 'foo', x: 'y' }
        }
      }, api)

      await store.dispatch(actions.setName(2, 'bar'))

      expect(api.setTabName).toHaveBeenCalledWith(2, 'bar')

      await tick()

      expect(store.getState().tabs['2']).toEqual({ name: 'bar', x: 'y' })
    })
  })

  describe('setOrder', () => {
    it('should set order', async () => {
      const api = {
        setTabOrder: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_ids: [ 1, 2 ],
          selected_tab_position: 0
        }
      }, api)

      await store.dispatch(actions.setOrder([ 2, 1 ]))

      expect(api.setTabOrder).toHaveBeenCalledWith([ 2, 1 ])

      expect(store.getState().workflow.tab_ids).toEqual([ 2, 1 ])
    })

    it('should update selected_tab_position', async () => {
      const api = {
        setTabOrder: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_ids: [ 1, 2, 3 ],
          selected_tab_position: 1 // tabId=2
        }
      }, api)

      await store.dispatch(actions.setOrder([ 3, 1, 2 ]))
      expect(store.getState().workflow.selected_tab_position).toEqual(2)
    })
  })

  describe('destroy', () => {
    it('should destroy the tab', async () => {
      const api = {
        deleteTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_ids: [ 1, 2 ],
          selected_tab_position: 0,
        },
        tabs: {
          1: { id: 1 },
          2: { id: 2 }
        }
      }, api)

      await store.dispatch(actions.destroy(2))
      expect(api.deleteTab).toHaveBeenCalledWith(2)
      const state = store.getState()
      expect(state.workflow.tab_ids).toEqual([ 1 ])
      expect(Object.keys(state.tabs)).toEqual([ '1' ])
    })

    it('should move selected_tab_position if selected is _after_ deleted', async () => {
      const api = {
        deleteTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_ids: [ 1, 2, 3 ],
          selected_tab_position: 2, // tab 3
        },
        tabs: {
          1: {},
          2: {},
          3: {}
        }
      }, api)

      await store.dispatch(actions.destroy(2))
      expect(store.getState().workflow.selected_tab_position).toEqual(1)
    })

    it('should leave selected_tab_position if selected is _before_ deleted', async () => {
      const api = {
        deleteTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_ids: [ 1, 2, 3 ],
          selected_tab_position: 1, // tab 2
        },
        tabs: {
          1: {},
          2: {},
          3: {}
        }
      }, api)

      await store.dispatch(actions.destroy(3))
      expect(store.getState().workflow.selected_tab_position).toEqual(1)
    })

    it('should move selected_tab_position if we deleted the last, selected tab', async () => {
      const api = {
        deleteTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_ids: [ 1, 2, 3 ],
          selected_tab_position: 2, // tab 3
        },
        tabs: {
          1: {},
          2: {},
          3: {}
        }
      }, api)

      await store.dispatch(actions.destroy(3))
      expect(store.getState().workflow.selected_tab_position).toEqual(1)
    })

    it('should move selected_tab_position if we deleted the first, selected tab', async () => {
      const api = {
        deleteTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_ids: [ 1, 2 ],
          selected_tab_position: 0, // tab 1
        },
        tabs: {
          1: {},
          2: {}
        }
      }, api)

      await store.dispatch(actions.destroy(1))
      expect(store.getState().workflow.selected_tab_position).toEqual(0) // tab 2
    })
  })

  describe('select', () => {
    it('should set selected_tab_position', async () => {
      const api = {
        setSelectedTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_ids: [ 1, 2 ],
          selected_tab_position: 0
        }
      }, api)

      await store.dispatch(actions.select(2))
      expect(api.setSelectedTab).toHaveBeenCalledWith(2)
      expect(store.getState().workflow.selected_tab_position).toEqual(1)
    })
  })

  describe('create', () => {
    it('should update workflow.pendingTabNames', async () => {
      let endDelay
      const delay = new Promise((resolve, reject) => {
        endDelay = resolve
      })
      const api = {
        // createTab(): takes one tick to fulfil
        createTab: jest.fn(() => delay)
      }
      const store = mockStore({
        workflow: {
        },
        tabs: {
          1: { name: 'A' }
        }
      }, api)

      await store.dispatch(actions.create())
      expect(api.createTab).toHaveBeenCalledWith('Tab 1')
      expect(store.getState().workflow.pendingTabNames).toEqual([ 'Tab 1' ])
      endDelay()
      await delay
      await tick()
      expect(store.getState().workflow.pendingTabNames).toEqual([])
    })

    it('should pick a new tab name based on current tab names', async () => {
      const api = {
        // createTab(): takes one tick to fulfil
        createTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
        },
        tabs: {
          1: { name: 'Tab 1' },
          3: { name: 'A' },
          4: { name: 'Tab 3' }
        }
      }, api)

      await store.dispatch(actions.create())
      expect(api.createTab).toHaveBeenCalledWith('Tab 4')
    })

    it('should consider pendingTabNames when deciding new tab names', async () => {
      const api = {
        // createTab(): takes one tick to fulfil
        createTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          pendingTabNames: [ 'Tab 14' ],
        },
        tabs: {
          1: { name: 'Tab 1' },
          3: { name: 'A' },
          4: { name: 'Tab 3' }
        }
      }, api)

      await store.dispatch(actions.create())
      expect(api.createTab).toHaveBeenCalledWith('Tab 15')
    })
  })
})
