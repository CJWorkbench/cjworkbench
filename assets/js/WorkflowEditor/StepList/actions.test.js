/* globals afterEach, beforeEach, describe, expect, it, jest */
import { mockStore } from '../../test-utils'
import { generateSlug } from '../../utils'
import selectOptimisticState from '../../selectors/selectOptimisticState'
import { applyDeltaAction } from '../../workflow-reducer'
import * as actions from './actions'

jest.mock('../../utils')

function selectStepSlugLists (state) {
  const { workflow, tabs, steps } = selectOptimisticState(state)
  return workflow.tab_slugs.map(tabSlug => ({
    tabSlug,
    stepSlugs: tabs[tabSlug].step_ids.map(id => steps[String(id)].slug)
  }))
}

describe('StepList.actions', () => {
  describe('reorderStep', () => {
    it('should call api.reorderSteps', async () => {
      let endDelay
      const delay = new Promise((resolve, reject) => { endDelay = resolve })
      const api = {
        reorderSteps: jest.fn(() => delay)
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['tab-1']
        },
        tabs: {
          'tab-1': {
            step_ids: [1, 2, 3]
          }
        },
        steps: {
          1: { id: 1, slug: 'step-1' },
          2: { id: 2, slug: 'step-2' },
          3: { id: 3, slug: 'step-3' }
        }
      }, api)

      generateSlug.mockImplementation(prefix => prefix + '1')
      const done = store.dispatch(actions.reorderStep('tab-1', 'step-3', 1))
      expect(api.reorderSteps).toHaveBeenCalledWith({
        mutationId: 'mutation-1',
        tabSlug: 'tab-1',
        slugs: ['step-1', 'step-3', 'step-2']
      })

      expect(store.getState().pendingMutations.map(u => u.id)).toEqual(['mutation-1'])
      expect(selectStepSlugLists(store.getState())).toEqual([{ tabSlug: 'tab-1', stepSlugs: ['step-1', 'step-3', 'step-2'] }])

      endDelay()
      await done
      // Optimistic update is still there
      expect(store.getState().pendingMutations.map(u => u.id)).toEqual(['mutation-1'])
      expect(selectStepSlugLists(store.getState())).toEqual([{ tabSlug: 'tab-1', stepSlugs: ['step-1', 'step-3', 'step-2'] }])

      await store.dispatch(applyDeltaAction({
        mutationId: 'mutation-1',
        updateTabs: {
          'tab-1': {
            step_ids: [1, 3, 2]
          }
        }
      }))
      // Optimistic update is gone: the real update took its place
      expect(store.getState().pendingMutations).toEqual([])
      expect(selectStepSlugLists(store.getState())).toEqual([{ tabSlug: 'tab-1', stepSlugs: ['step-1', 'step-3', 'step-2'] }])
      expect(console.warn).not.toHaveBeenCalled()
    })

    // Fiddle with console.warn because workflowReducer logs on unhandled error
    const originalWarn = console.warn
    beforeEach(() => { global.console.warn = jest.fn() })
    afterEach(() => { global.console.warn = originalWarn })

    it('should ignore reorder when a step has gone away', async () => {
      let endDelayAndReject
      const delay = new Promise((resolve, reject) => { endDelayAndReject = reject })
      const api = {
        reorderSteps: jest.fn(() => delay)
      }
      const store = mockStore({
        workflow: {
          tab_slugs: ['tab-1']
        },
        tabs: {
          'tab-1': {
            step_ids: [1, 2, 3]
          }
        },
        steps: {
          1: { id: 1, slug: 'step-1' },
          2: { id: 2, slug: 'step-2' },
          3: { id: 3, slug: 'step-3' }
        }
      }, api)

      generateSlug.mockImplementation(prefix => prefix + '1')
      const done = store.dispatch(actions.reorderStep('tab-1', 'step-3', 1))
      expect(api.reorderSteps).toHaveBeenCalledWith({
        mutationId: 'mutation-1',
        tabSlug: 'tab-1',
        slugs: ['step-1', 'step-3', 'step-2']
      })

      await store.dispatch(applyDeltaAction({
        mutationId: 'mutation-not-ours',
        updateTabs: {
          'tab-1': {
            step_ids: [2, 3]
          }
        },
        clearStepIds: [1]
      }))

      // Optimistic update is a no-op
      expect(store.getState().pendingMutations.map(u => u.id)).toEqual(['mutation-1'])
      expect(selectStepSlugLists(store.getState())).toEqual([{ tabSlug: 'tab-1', stepSlugs: ['step-2', 'step-3'] }])

      endDelayAndReject(new Error('Something from the server'))
      await done
      // Optimistic update is gone
      expect(store.getState().pendingMutations).toEqual([])
      expect(selectStepSlugLists(store.getState())).toEqual([{ tabSlug: 'tab-1', stepSlugs: ['step-2', 'step-3'] }])
      expect(console.warn).toHaveBeenCalled()
      expect(console.warn.mock.calls[0][0]).toEqual('reorderSteps failed')
    })
  })
})
