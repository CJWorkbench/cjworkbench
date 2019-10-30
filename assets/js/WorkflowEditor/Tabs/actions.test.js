/* globals describe, expect, it, jest */
import { mockStore } from '../../test-utils'
import { generateSlug } from '../../utils'
import * as actions from './actions'

jest.mock('../../utils')

describe('Tabs.actions', () => {
  describe('setName', () => {
    it('should setName', async () => {
      let endDelay
      const delay = new Promise((resolve, reject) => { endDelay = resolve })
      const api = {
        setTabName: jest.fn(() => delay)
      }
      const store = mockStore({
        tabs: {
          t2: { name: 'foo', x: 'y' }
        }
      }, api)

      const done = store.dispatch(actions.setName('t2', 'bar'))
      expect(api.setTabName).toHaveBeenCalledWith('t2', 'bar')
      expect(store.getState().tabs.t2).toEqual({ name: 'bar', x: 'y' })

      endDelay()
      await done
    })
  })

  describe('setOrder', () => {
    it('should set order', async () => {
      const api = {
        setTabOrder: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        selectedPane: { pane: 'tab', tabSlug: 't1' },
        workflow: {
          tab_slugs: ['t1', 't2'],
          selected_tab_position: 0
        }
      }, api)

      await store.dispatch(actions.setOrder(['t2', 't1']))

      expect(api.setTabOrder).toHaveBeenCalledWith(['t2', 't1'])

      expect(store.getState().workflow.tab_slugs).toEqual(['t2', 't1'])
    })

    it('should update selected_tab_position', async () => {
      const api = {
        setTabOrder: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['t1', 't2', 't3'],
          selected_tab_position: 1 // tabSlug=t2
        }
      }, api)

      await store.dispatch(actions.setOrder(['t3', 't1', 't2']))
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
          tab_slugs: ['t1', 't2'],
          selected_tab_position: 0
        },
        selectedPane: {
          pane: 'tab',
          tabSlug: 't1'
        },
        tabs: {
          t1: { slug: 't1' },
          t2: { slug: 't2' }
        }
      }, api)

      await store.dispatch(actions.destroy('t2'))
      expect(api.deleteTab).toHaveBeenCalledWith('t2')
      const state = store.getState()
      expect(state.workflow.tab_slugs).toEqual(['t1'])
      expect(Object.keys(state.tabs)).toEqual(['t1'])
    })

    it('should destroy a pending tab', async () => {
      const api = {
        deleteTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['t1', 't2'],
          selected_tab_position: 0
        },
        selectedPane: {
          pane: 'tab',
          tabSlug: 't1'
        },
        pendingTabs: {
          t2: { slug: 't2' }
        },
        tabs: {
          t1: { slug: 't1' }
        }
      }, api)

      await store.dispatch(actions.destroy('t2'))
      // The client calls this before even _knowing_ that it's been created on
      // the server. But since it's in `pendingTabs`, we _assume_ it will exist
      // on the server at the time `api.deleteTab()` will be called.
      expect(api.deleteTab).toHaveBeenCalledWith('t2')
      const state = store.getState()
      expect(state.workflow.tab_slugs).toEqual(['t1'])
      expect(Object.keys(state.tabs)).toEqual(['t1'])
      expect(state.pendingTabs).toEqual({})
    })

    it('should not destroy the only remaining tab', async () => {
      const api = {
        deleteTab: jest.fn()
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['t1'],
          selected_tab_position: 0
        },
        tabs: {
          t1: {}
        }
      }, api)

      await store.dispatch(actions.destroy('t1'))
      expect(api.deleteTab).not.toHaveBeenCalled()
      const state = store.getState()
      expect(state.workflow.tab_slugs).toEqual(['t1'])
      expect(Object.keys(state.tabs)).toEqual(['t1'])
    })

    it('should move selected_tab_position and selectedPane when destroying selected', async () => {
      const api = {
        deleteTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        selectedPane: {
          pane: 'tab',
          tabSlug: 't2'
        },
        workflow: {
          tab_slugs: ['t1', 't2', 't3'],
          selected_tab_position: 1 // tab t2
        },
        tabs: {
          t1: {},
          t2: {},
          t3: {}
        }
      }, api)

      await store.dispatch(actions.destroy('t2'))
      expect(store.getState().workflow.selected_tab_position).toEqual(0)
      expect(store.getState().selectedPane).toEqual({ pane: 'tab', tabSlug: 't1' })
    })

    it('should move selected_tab_position if selected is _after_ deleted', async () => {
      const api = {
        deleteTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['t1', 't2', 't3'],
          selected_tab_position: 2 // tab t3
        },
        selectedPane: {
          pane: 'tab',
          tabSlug: 't3'
        },
        tabs: {
          t1: {},
          t2: {},
          t3: {}
        }
      }, api)

      await store.dispatch(actions.destroy('t2'))
      expect(store.getState().workflow.selected_tab_position).toEqual(1)
      expect(store.getState().selectedPane).toEqual({ pane: 'tab', tabSlug: 't3' })
    })

    it('should leave selected_tab_position and selectedPane if selected is _before_ deleted', async () => {
      const api = {
        deleteTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['t1', 't2', 't3'],
          selected_tab_position: 1 // tab t2
        },
        selectedPane: {
          pane: 'tab',
          tabSlug: 't2'
        },
        tabs: {
          t1: {},
          t2: {},
          t3: {}
        }
      }, api)

      await store.dispatch(actions.destroy('t3'))
      expect(store.getState().workflow.selected_tab_position).toEqual(1)
      expect(store.getState().selectedPane).toEqual({ pane: 'tab', tabSlug: 't2' })
    })

    it('should move selected_tab_position if we deleted the last, selected tab', async () => {
      const api = {
        deleteTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['t1', 't2', 't3'],
          selected_tab_position: 2 // tab t3
        },
        selectedPane: {
          pane: 'tab',
          tabSlug: 't3'
        },
        tabs: {
          t1: {},
          t2: {},
          t3: {}
        }
      }, api)

      await store.dispatch(actions.destroy('t3'))
      expect(store.getState().workflow.selected_tab_position).toEqual(1)
      expect(store.getState().selectedPane).toEqual({ pane: 'tab', tabSlug: 't2' })
    })

    it('should move selected_tab_position if we deleted the first, selected tab', async () => {
      const api = {
        deleteTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['t1', 't2'],
          selected_tab_position: 0 // tab 1
        },
        selectedPane: {
          pane: 'tab',
          tabSlug: 't1'
        },
        tabs: {
          t1: {},
          t2: {}
        }
      }, api)

      await store.dispatch(actions.destroy('t1'))
      expect(store.getState().workflow.selected_tab_position).toEqual(0) // tab t2
      expect(store.getState().selectedPane).toEqual({ pane: 'tab', tabSlug: 't2' })
    })
  })

  describe('select', () => {
    it('should set selected_tab_position (to new server value) and selectedPane', async () => {
      const api = {
        setSelectedTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['t1', 't2'],
          selected_tab_position: 0
        }
      }, api)

      await store.dispatch(actions.select('t2'))
      expect(api.setSelectedTab).toHaveBeenCalledWith('t2')
      expect(store.getState().selectedPane).toEqual({ pane: 'tab', tabSlug: 't2' })
      expect(store.getState().workflow.selected_tab_position).toEqual(1)
    })

    it('should skip api when read-only', async () => {
      const api = {
        setSelectedTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['t1', 't2'],
          selected_tab_position: 0,
          read_only: true
        }
      }, api)

      await store.dispatch(actions.select('t2'))
      expect(api.setSelectedTab).not.toHaveBeenCalled()
      expect(store.getState().selectedPane).toEqual({ pane: 'tab', tabSlug: 't2' })
      expect(store.getState().workflow.selected_tab_position).toEqual(1)
    })

    it('should ignore invalid tab slug', async () => {
      // This happens if the user clicks a "delete" button on the module:
      // 2. Browser dispatches "delete", which removes the tab
      // 1. Browser dispatches "click", which tries to select it
      // https://www.pivotaltracker.com/story/show/162803752
      const api = {
        setSelectedTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['t1', 't2'],
          selected_tab_position: 0
        }
      }, api)

      await store.dispatch(actions.select('t3'))
      expect(api.setSelectedTab).not.toHaveBeenCalled()
      expect(store.getState().workflow.selected_tab_position).toEqual(0)
    })
  })

  describe('create', () => {
    it('should update workflow.pendingTabs', async () => {
      let endDelay
      const delay = new Promise((resolve, reject) => { endDelay = resolve })
      const api = {
        createTab: jest.fn(() => delay)
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['t1']
        },
        tabs: {
          t1: { name: 'A' }
        }
      }, api)

      generateSlug.mockImplementationOnce(prefix => prefix + 'X')
      const done = store.dispatch(actions.create('Tab'))
      expect(api.createTab).toHaveBeenCalledWith('tab-X', 'Tab 1')
      expect(store.getState().workflow.tab_slugs).toEqual(['t1', 'tab-X'])
      expect(store.getState().pendingTabs).toEqual({
        'tab-X': {
          slug: 'tab-X',
          name: 'Tab 1',
          wf_module_ids: [],
          selected_wf_module_position: null
        }
      })
      endDelay()
      await done
      // pendingTabs can't change. Only _after_ the action finishes will we
      // receive a new delta from the server with the new tab ID. That new
      // _delta_ is where we should be deleting from pendingTabs.
      expect(store.getState().pendingTabs).toEqual({
        'tab-X': {
          slug: 'tab-X',
          name: 'Tab 1',
          wf_module_ids: [],
          selected_wf_module_position: null
        }
      })
    })

    it('should pick a new tab name based on current tab names', async () => {
      const api = {
        createTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['t1', 't3', 't4']
        },
        tabs: {
          t1: { name: 'Tab 1' },
          t3: { name: 'A' },
          t4: { name: 'Tab 3' }
        }
      }, api)

      generateSlug.mockImplementationOnce(prefix => prefix + 'X')
      await store.dispatch(actions.create('Tab'))
      expect(api.createTab).toHaveBeenCalledWith('tab-X', 'Tab 4')
    })

    it('should consider pendingTabs when deciding new tab names', async () => {
      const api = {
        createTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['t1', 't3', 't4']
        },
        pendingTabs: {
          t14: { name: 'Tab 14' }
        },
        tabs: {
          t1: { name: 'Tab 1' },
          t3: { name: 'A' },
          t4: { name: 'Tab 3' }
        }
      }, api)

      generateSlug.mockImplementationOnce(prefix => prefix + 'X')
      await store.dispatch(actions.create('Tab'))
      expect(api.createTab).toHaveBeenCalledWith('tab-X', 'Tab 15')
    })
  })

  describe('duplicate', () => {
    it('should update workflow.tab_slugs and workflow.pendingTabs', async () => {
      let endDelay
      const delay = new Promise((resolve, reject) => { endDelay = resolve })
      const api = {
        duplicateTab: jest.fn(() => delay)
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['t1', 't2'] // and we'll "duplicate" in between
        },
        tabs: {
          t1: { name: 'A' },
          t2: { name: 'B' }
        }
      }, api)

      generateSlug.mockImplementationOnce(prefix => prefix + 'X')
      const done = store.dispatch(actions.duplicate('t1'))
      expect(api.duplicateTab).toHaveBeenCalledWith('t1', 'tab-X', 'A (1)')
      expect(store.getState().workflow.tab_slugs).toEqual(['t1', 'tab-X', 't2'])
      expect(store.getState().pendingTabs).toEqual({
        'tab-X': {
          slug: 'tab-X',
          name: 'A (1)',
          wf_module_ids: [],
          selected_wf_module_position: null
        }
      })
      endDelay()
      await done
      // pendingTabs can't change. Only _after_ the action finishes will we
      // receive a new delta from the server with the new tab ID. That new
      // _delta_ is where we should be deleting from pendingTabs.
      expect(store.getState().pendingTabs).toEqual({
        'tab-X': {
          slug: 'tab-X',
          name: 'A (1)',
          wf_module_ids: [],
          selected_wf_module_position: null
        }
      })
    })

    it('should pick a new tab name based on current tab names', async () => {
      const api = {
        duplicateTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['t1', 't3', 't4']
        },
        tabs: {
          t1: { name: 'A' },
          t2: { name: 'A (1)' }
        }
      }, api)

      generateSlug.mockImplementationOnce(prefix => prefix + 'X')
      await store.dispatch(actions.duplicate('t2'))
      expect(api.duplicateTab).toHaveBeenCalledWith('t2', 'tab-X', 'A (2)')
    })

    it('should consider pendingTabs when deciding new tab names', async () => {
      const api = {
        duplicateTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['t1', 't3', 't4']
        },
        pendingTabs: {
          t14: { name: 'A (14)' }
        },
        tabs: {
          t1: { name: 'Tab 1' },
          t3: { name: 'A' },
          t4: { name: 'Tab 3' }
        }
      }, api)

      generateSlug.mockImplementationOnce(prefix => prefix + 'X')
      await store.dispatch(actions.duplicate('t3'))
      expect(api.duplicateTab).toHaveBeenCalledWith('t3', 'tab-X', 'A (15)')
    })
  })
})
