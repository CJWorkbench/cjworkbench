/* globals describe, expect, it, jest */
import { mockStore } from '../../test-utils'
import { generateSlug } from '../../utils'
import * as actions from './actions'
import selectOptimisticState from '../../selectors/selectOptimisticState'

jest.mock('../../utils')

describe('Tabs.actions', () => {
  describe('setName', () => {
    it('should setName', async () => {
      let endDelay
      const delay = new Promise((resolve, reject) => {
        endDelay = resolve
      })
      const api = {
        setTabName: jest.fn(() => delay)
      }
      const store = mockStore(
        {
          tabs: {
            t2: { name: 'foo', x: 'y' }
          }
        },
        api
      )

      generateSlug.mockImplementation(prefix => prefix + 'X')
      const done = store.dispatch(actions.setName('t2', 'bar'))
      expect(api.setTabName).toHaveBeenCalledWith('t2', 'bar', 'mutation-X')
      expect(selectOptimisticState(store.getState()).tabs.t2).toEqual({ name: 'bar', x: 'y' })

      endDelay()
      await done
    })
  })

  describe('setOrder', () => {
    it('should set order', async () => {
      const api = {
        setTabOrder: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore(
        {
          selectedPane: { pane: 'tab', tabSlug: 't1' },
          workflow: {
            tab_slugs: ['t1', 't2']
          }
        },
        api
      )

      generateSlug.mockImplementation(prefix => prefix + 'X')
      await store.dispatch(actions.setOrder(['t2', 't1']))

      expect(api.setTabOrder).toHaveBeenCalledWith(['t2', 't1'], 'mutation-X')

      expect(selectOptimisticState(store.getState()).workflow.tab_slugs).toEqual(['t2', 't1'])
    })
  })

  describe('destroy', () => {
    it('should destroy the tab', async () => {
      const api = {
        deleteTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore(
        {
          workflow: {
            tab_slugs: ['t1', 't2']
          },
          selectedPane: {
            pane: 'tab',
            tabSlug: 't1'
          },
          tabs: {
            t1: { slug: 't1' },
            t2: { slug: 't2' }
          }
        },
        api
      )

      generateSlug.mockImplementation(prefix => prefix + 'X')
      await store.dispatch(actions.destroy('t2'))
      expect(api.deleteTab).toHaveBeenCalledWith('t2', 'mutation-X')
      const state = selectOptimisticState(store.getState())
      expect(state.workflow.tab_slugs).toEqual(['t1'])
      expect(Object.keys(state.tabs)).toEqual(['t1'])
    })

    it('should destroy a pending tab', async () => {
      const api = {
        createTab: jest.fn(() => Promise.resolve(null)),
        deleteTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore(
        {
          workflow: {
            tab_slugs: ['t1']
          },
          selectedPane: {
            pane: 'tab',
            tabSlug: 't1'
          },
          tabs: {
            t1: { slug: 't1' }
          }
        },
        api
      )

      generateSlug.mockImplementation(prefix => prefix + 'X')
      const promise1 = store.dispatch(actions.create('Tab'))
      generateSlug.mockImplementation(prefix => prefix + 'Y')
      const promise2 = store.dispatch(actions.destroy('tab-X'))

      let state = selectOptimisticState(store.getState())
      expect(state.workflow.tab_slugs).toEqual(['t1'])
      expect(Object.keys(state.tabs)).toEqual(['t1'])

      await promise1
      state = selectOptimisticState(store.getState())
      expect(state.workflow.tab_slugs).toEqual(['t1'])
      expect(Object.keys(state.tabs)).toEqual(['t1'])
      await promise2
      expect(api.deleteTab).toHaveBeenCalledWith('tab-X', 'mutation-Y')
      state = selectOptimisticState(store.getState())
      expect(state.workflow.tab_slugs).toEqual(['t1'])
      expect(Object.keys(state.tabs)).toEqual(['t1'])
    })

    it('should not destroy the only remaining tab', async () => {
      const api = {
        deleteTab: jest.fn()
      }
      const store = mockStore(
        {
          workflow: {
            tab_slugs: ['t1']
          },
          tabs: {
            t1: {}
          }
        },
        api
      )

      await store.dispatch(actions.destroy('t1'))
      expect(api.deleteTab).not.toHaveBeenCalled()
      const state = selectOptimisticState(store.getState())
      expect(state.workflow.tab_slugs).toEqual(['t1'])
      expect(Object.keys(state.tabs)).toEqual(['t1'])
    })

    it('should move selectedPane when destroying selected', async () => {
      const api = {
        deleteTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore(
        {
          selectedPane: {
            pane: 'tab',
            tabSlug: 't2'
          },
          workflow: {
            tab_slugs: ['t1', 't2', 't3']
          },
          tabs: {
            t1: {},
            t2: {},
            t3: {}
          }
        },
        api
      )

      await store.dispatch(actions.destroy('t2'))
      expect(selectOptimisticState(store.getState()).selectedPane).toEqual({
        pane: 'tab',
        tabSlug: 't1'
      })
    })
  })

  describe('select', () => {
    it('should skip api when read-only', async () => {
      const api = {
        setSelectedTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore(
        {
          loggedInUser: null,
          workflow: {
            tab_slugs: ['t1', 't2'],
            public: false,
            owner_email: 'alice@example.com',
            acl: []
          }
        },
        api
      )

      await store.dispatch(actions.select('t2'))
      expect(api.setSelectedTab).not.toHaveBeenCalled()
      expect(selectOptimisticState(store.getState()).selectedPane).toEqual({
        pane: 'tab',
        tabSlug: 't2'
      })
    })

    it('should ignore invalid tab slug', async () => {
      // This happens if the user clicks a "delete" button on the module:
      // 2. Browser dispatches "delete", which removes the tab
      // 1. Browser dispatches "click", which tries to select it
      // https://www.pivotaltracker.com/story/show/162803752
      const api = {
        setSelectedTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore(
        {
          workflow: {
            tab_slugs: ['t1', 't2']
          }
        },
        api
      )

      await store.dispatch(actions.select('t3'))
      expect(api.setSelectedTab).not.toHaveBeenCalled()
    })
  })

  describe('create', () => {
    it('should update workflow.tab_slugs', async () => {
      let endDelay
      const delay = new Promise((resolve, reject) => {
        endDelay = resolve
      })
      const api = {
        createTab: jest.fn(() => delay)
      }
      const store = mockStore(
        {
          workflow: {
            tab_slugs: ['t1']
          },
          tabs: {
            t1: { name: 'A' }
          }
        },
        api
      )

      generateSlug.mockImplementation(prefix => prefix + 'X')
      const done = store.dispatch(actions.create('Tab'))
      expect(api.createTab).toHaveBeenCalledWith('tab-X', 'Tab 1', 'mutation-X')
      expect(selectOptimisticState(store.getState()).workflow.tab_slugs).toEqual(['t1', 'tab-X'])
      expect(selectOptimisticState(store.getState()).tabs['tab-X']).toEqual({
        slug: 'tab-X',
        name: 'Tab 1',
        step_ids: [],
        selected_step_position: null
      })
      endDelay()
      await done
      expect(selectOptimisticState(store.getState()).workflow.tab_slugs).toEqual(['t1', 'tab-X'])
      expect(selectOptimisticState(store.getState()).tabs['tab-X']).toEqual({
        slug: 'tab-X',
        name: 'Tab 1',
        step_ids: [],
        selected_step_position: null
      })
    })

    it('should pick a new tab name based on current tab names', async () => {
      const api = {
        createTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore(
        {
          workflow: {
            tab_slugs: ['t1', 't3', 't4']
          },
          tabs: {
            t1: { name: 'Tab 1' },
            t3: { name: 'A' },
            t4: { name: 'Tab 3' }
          }
        },
        api
      )

      generateSlug.mockImplementation(prefix => prefix + 'X')
      await store.dispatch(actions.create('Tab'))
      expect(api.createTab).toHaveBeenCalledWith('tab-X', 'Tab 4', 'mutation-X')
    })

    it('should consider pending tabs when deciding new tab names', async () => {
      const api = {
        createTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore(
        {
          workflow: {
            tab_slugs: ['t1', 't4']
          },
          tabs: {
            t1: { name: 'Tab 1' },
            t4: { name: 'Tab 4' }
          }
        },
        api
      )

      generateSlug.mockImplementation(prefix => prefix + 'X')
      const promise1 = store.dispatch(actions.create('Tab'))
      expect(api.createTab).toHaveBeenCalledWith('tab-X', 'Tab 5', 'mutation-X')
      generateSlug.mockImplementation(prefix => prefix + 'Y')
      const promise2 = store.dispatch(actions.create('Tab'))
      expect(api.createTab).toHaveBeenCalledWith('tab-Y', 'Tab 6', 'mutation-Y')

      expect(Object.values(selectOptimisticState(store.getState()).tabs).map(tab => tab.name))
        .toEqual(['Tab 1', 'Tab 4', 'Tab 5', 'Tab 6'])
      await promise1
      expect(Object.values(selectOptimisticState(store.getState()).tabs).map(tab => tab.name))
        .toEqual(['Tab 1', 'Tab 4', 'Tab 5', 'Tab 6'])
      await promise2
      expect(Object.values(selectOptimisticState(store.getState()).tabs).map(tab => tab.name))
        .toEqual(['Tab 1', 'Tab 4', 'Tab 5', 'Tab 6'])
    })
  })

  describe('duplicate', () => {
    it('should update workflow.tab_slugs and workflow.tabs', async () => {
      let endDelay
      const delay = new Promise((resolve, reject) => {
        endDelay = resolve
      })
      const api = {
        duplicateTab: jest.fn(() => delay)
      }
      const store = mockStore(
        {
          workflow: {
            tab_slugs: ['t1', 't2'] // and we'll "duplicate" in between
          },
          tabs: {
            t1: { name: 'A' },
            t2: { name: 'B' }
          }
        },
        api
      )

      generateSlug.mockImplementation(prefix => prefix + 'X')
      const done = store.dispatch(actions.duplicate('t1'))
      expect(api.duplicateTab).toHaveBeenCalledWith('t1', 'tab-X', 'A (1)', 'mutation-X')
      expect(selectOptimisticState(store.getState()).workflow.tab_slugs).toEqual(['t1', 'tab-X', 't2'])
      expect(selectOptimisticState(store.getState()).tabs['tab-X']).toEqual({
        slug: 'tab-X',
        name: 'A (1)',
        step_ids: [],
        selected_step_position: null
      })
      endDelay()
      await done
      expect(selectOptimisticState(store.getState()).tabs['tab-X']).toEqual({
        slug: 'tab-X',
        name: 'A (1)',
        step_ids: [],
        selected_step_position: null
      })
    })

    it('should pick a new tab name based on current tab names', async () => {
      const api = {
        duplicateTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore(
        {
          workflow: {
            tab_slugs: ['t1', 't3', 't4']
          },
          tabs: {
            t1: { name: 'A' },
            t2: { name: 'A (1)' }
          }
        },
        api
      )

      generateSlug.mockImplementation(prefix => prefix + 'X')
      await store.dispatch(actions.duplicate('t2'))
      expect(api.duplicateTab).toHaveBeenCalledWith('t2', 'tab-X', 'A (2)', 'mutation-X')
    })

    it('should consider pending tabs when deciding new tab names', async () => {
      const api = {
        duplicateTab: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore(
        {
          workflow: {
            tab_slugs: ['t1', 'tA', 't4']
          },
          tabs: {
            t1: { name: 'Tab 1' },
            tA: { name: 'A' },
            t4: { name: 'Tab 3' }
          }
        },
        api
      )

      generateSlug.mockImplementation(prefix => prefix + 'X')
      const promise1 = store.dispatch(actions.duplicate('tA'))
      expect(api.duplicateTab).toHaveBeenCalledWith('tA', 'tab-X', 'A (1)', 'mutation-X')
      generateSlug.mockImplementation(prefix => prefix + 'Y')
      const promise2 = store.dispatch(actions.duplicate('tA'))
      expect(api.duplicateTab).toHaveBeenLastCalledWith('tA', 'tab-Y', 'A (2)', 'mutation-Y')

      await promise1
      await promise2
    })
  })
})
