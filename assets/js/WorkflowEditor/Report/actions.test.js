/* globals afterEach, beforeEach, describe, expect, it, jest */
import { mockStore } from '../../test-utils'
import { generateSlug } from '../../utils'
import selectReport from '../../selectors/selectReport'
import selectOptimisticState from '../../selectors/selectOptimisticState'
import { applyDeltaAction } from '../../workflow-reducer'
import * as actions from './actions'

jest.mock('../../utils')

describe('Report.actions', () => {
  describe('addBlock', () => {
    it('should call api.addBlock', async () => {
      let endDelay
      const delay = new Promise((resolve, reject) => {
        endDelay = resolve
      })
      const api = {
        addBlock: jest.fn(() => delay)
      }
      const store = mockStore(
        {
          workflow: {
            hasCustomReport: true,
            blockSlugs: ['block-1', 'block-2']
          },
          tabs: {},
          steps: {},
          blocks: {
            'block-1': { type: 'text', markdown: 'hi' },
            'block-2': { type: 'text', markdown: 'bye' }
          },
          selectedPane: {}
        },
        api
      )

      const expectedReport = [
        { slug: 'block-1', type: 'text', markdown: 'hi' },
        { slug: 'block-3', type: 'text', markdown: 'new' },
        { slug: 'block-2', type: 'text', markdown: 'bye' }
      ]

      generateSlug.mockImplementation(prefix => prefix + '3')
      const done = store.dispatch(
        actions.addBlock(1, { type: 'text', markdown: 'new' })
      )
      expect(api.addBlock).toHaveBeenCalledWith({
        slug: 'block-3',
        position: 1,
        mutationId: 'mutation-3',
        type: 'text',
        markdown: 'new'
      })

      expect(store.getState().pendingMutations.map(u => u.id)).toEqual([
        'mutation-3'
      ])
      expect(selectReport(store.getState())).toEqual(expectedReport)

      endDelay()
      await done
      // Optimistic update is still there
      expect(store.getState().pendingMutations.map(u => u.id)).toEqual([
        'mutation-3'
      ])
      expect(selectReport(store.getState())).toEqual(expectedReport)

      await store.dispatch(
        applyDeltaAction({
          mutationId: 'mutation-3',
          updateWorkflow: {
            blockSlugs: ['block-1', 'block-3', 'block-2']
          },
          updateBlocks: {
            'block-3': { type: 'text', markdown: 'new' }
          }
        })
      )
      // Optimistic update is gone: the real update took its place
      expect(store.getState().pendingMutations).toEqual([])
      expect(selectReport(store.getState())).toEqual(expectedReport)
    })

    it('should expand auto-report before add', async () => {
      let endDelay
      const delay = new Promise((resolve, reject) => {
        endDelay = resolve
      })
      const api = {
        addBlock: jest.fn(() => delay)
      }
      const step1 = { slug: 'step-1', module: 'chart' }
      const store = mockStore(
        {
          workflow: {
            hasCustomReport: false,
            blockSlugs: [],
            tab_slugs: ['tab-1']
          },
          tabs: {
            'tab-1': { step_ids: [1] }
          },
          steps: {
            1: step1
          },
          modules: {
            chart: { has_html_output: true }
          },
          blocks: {},
          selectedPane: {}
        },
        api
      )

      const expectedReport = [
        { slug: 'block-auto-step-1', type: 'chart', step: step1 },
        { slug: 'block-foo', type: 'text', markdown: 'new' }
      ]

      generateSlug.mockImplementation(prefix => prefix + 'foo')
      const done = store.dispatch(
        actions.addBlock(1, { type: 'text', markdown: 'new' })
      )
      expect(api.addBlock).toHaveBeenCalledWith({
        slug: 'block-foo',
        position: 1,
        mutationId: 'mutation-foo',
        type: 'text',
        markdown: 'new'
      })

      expect(store.getState().pendingMutations.map(u => u.id)).toEqual([
        'mutation-foo'
      ])
      expect(
        selectOptimisticState(store.getState()).workflow.hasCustomReport
      ).toBe(true)
      expect(selectReport(store.getState())).toEqual(expectedReport)

      endDelay()
      await done
      // Optimistic update is still there
      expect(store.getState().pendingMutations.map(u => u.id)).toEqual([
        'mutation-foo'
      ])
      expect(
        selectOptimisticState(store.getState()).workflow.hasCustomReport
      ).toBe(true)
      expect(selectReport(store.getState())).toEqual(expectedReport)

      await store.dispatch(
        applyDeltaAction({
          mutationId: 'mutation-foo',
          updateWorkflow: {
            hasCustomReport: true,
            blockSlugs: ['block-auto-step-1', 'block-foo']
          },
          updateBlocks: {
            'block-auto-step-1': { type: 'chart', stepSlug: 'step-1' },
            'block-foo': { type: 'text', markdown: 'new' }
          }
        })
      )
      // Optimistic update is gone: the real update took its place
      expect(store.getState().pendingMutations).toEqual([])
      expect(selectReport(store.getState())).toEqual(expectedReport)
      expect(
        selectOptimisticState(store.getState()).workflow.hasCustomReport
      ).toBe(true)
    })
  })

  describe('deleteBlock', () => {
    it('should call api.deleteBlock', async () => {
      let endDelay
      const delay = new Promise((resolve, reject) => {
        endDelay = resolve
      })
      const api = {
        deleteBlock: jest.fn(() => delay)
      }
      const store = mockStore(
        {
          workflow: {
            hasCustomReport: true,
            blockSlugs: ['block-1', 'block-2']
          },
          tabs: {},
          steps: {},
          blocks: {
            'block-1': { type: 'text', markdown: 'hi' },
            'block-2': { type: 'text', markdown: 'bye' }
          },
          selectedPane: {}
        },
        api
      )

      const expectedReport = [{ slug: 'block-1', type: 'text', markdown: 'hi' }]

      generateSlug.mockImplementation(prefix => prefix + '1')
      const done = store.dispatch(actions.deleteBlock('block-2'))
      expect(api.deleteBlock).toHaveBeenCalledWith({
        mutationId: 'mutation-1',
        slug: 'block-2'
      })

      expect(store.getState().pendingMutations.map(u => u.id)).toEqual([
        'mutation-1'
      ])
      expect(selectReport(store.getState())).toEqual(expectedReport)

      endDelay()
      await done
      // Optimistic update is still there
      expect(store.getState().pendingMutations.map(u => u.id)).toEqual([
        'mutation-1'
      ])
      expect(selectReport(store.getState())).toEqual(expectedReport)

      await store.dispatch(
        applyDeltaAction({
          mutationId: 'mutation-1',
          updateWorkflow: { blockSlugs: ['block-1'] },
          clearBlockSlugs: ['block-2']
        })
      )
      // Optimistic update is gone: the real update took its place
      expect(store.getState().pendingMutations).toEqual([])
      expect(selectReport(store.getState())).toEqual(expectedReport)
    })

    it('should expand auto-report before delete', async () => {
      let endDelay
      const delay = new Promise((resolve, reject) => {
        endDelay = resolve
      })
      const api = {
        deleteBlock: jest.fn(() => delay)
      }
      const step1 = { slug: 'step-1', module: 'chart' }
      const store = mockStore(
        {
          workflow: {
            hasCustomReport: false,
            blockSlugs: [],
            tab_slugs: ['tab-1']
          },
          tabs: {
            'tab-1': { step_ids: [1, 2] }
          },
          steps: {
            1: step1,
            2: { slug: 'step-2', module: 'chart' }
          },
          modules: {
            chart: { has_html_output: true }
          },
          blocks: {},
          selectedPane: {}
        },
        api
      )

      const expectedReport = [
        { slug: 'block-auto-step-1', type: 'chart', step: step1 }
      ]

      generateSlug.mockImplementation(prefix => prefix + '1')
      const done = store.dispatch(actions.deleteBlock('block-auto-step-2'))
      expect(api.deleteBlock).toHaveBeenCalledWith({
        mutationId: 'mutation-1',
        slug: 'block-auto-step-2'
      })

      expect(store.getState().pendingMutations.map(u => u.id)).toEqual([
        'mutation-1'
      ])
      expect(
        selectOptimisticState(store.getState()).workflow.hasCustomReport
      ).toBe(true)
      expect(selectReport(store.getState())).toEqual(expectedReport)

      endDelay()
      await done
      // Optimistic update is still there
      expect(store.getState().pendingMutations.map(u => u.id)).toEqual([
        'mutation-1'
      ])
      expect(
        selectOptimisticState(store.getState()).workflow.hasCustomReport
      ).toBe(true)
      expect(selectReport(store.getState())).toEqual(expectedReport)

      await store.dispatch(
        applyDeltaAction({
          mutationId: 'mutation-1',
          updateWorkflow: {
            hasCustomReport: true,
            blockSlugs: ['block-auto-step-1']
          },
          updateBlocks: {
            'block-auto-step-1': { type: 'chart', stepSlug: 'step-1' }
          }
        })
      )
      // Optimistic update is gone: the real update took its place
      expect(store.getState().pendingMutations).toEqual([])
      expect(selectReport(store.getState())).toEqual(expectedReport)
      expect(
        selectOptimisticState(store.getState()).workflow.hasCustomReport
      ).toBe(true)
    })
  })

  describe('reorderBlocks', () => {
    it('should call api.reorderBlocks', async () => {
      let endDelay
      const delay = new Promise((resolve, reject) => {
        endDelay = resolve
      })
      const api = {
        reorderBlocks: jest.fn(() => delay)
      }
      const store = mockStore(
        {
          workflow: {
            hasCustomReport: true,
            blockSlugs: ['block-1', 'block-2']
          },
          tabs: {},
          steps: {},
          blocks: {
            'block-1': { type: 'text', markdown: 'hi' },
            'block-2': { type: 'text', markdown: 'bye' }
          },
          selectedPane: {}
        },
        api
      )

      const expectedReport = [
        { slug: 'block-2', type: 'text', markdown: 'bye' },
        { slug: 'block-1', type: 'text', markdown: 'hi' }
      ]

      generateSlug.mockImplementation(prefix => prefix + '1')
      const done = store.dispatch(actions.reorderBlocks(['block-2', 'block-1']))
      expect(api.reorderBlocks).toHaveBeenCalledWith({
        mutationId: 'mutation-1',
        slugs: ['block-2', 'block-1']
      })

      expect(store.getState().pendingMutations.map(u => u.id)).toEqual([
        'mutation-1'
      ])
      expect(selectReport(store.getState())).toEqual(expectedReport)

      endDelay()
      await done
      // Optimistic update is still there
      expect(store.getState().pendingMutations.map(u => u.id)).toEqual([
        'mutation-1'
      ])
      expect(selectReport(store.getState())).toEqual(expectedReport)

      await store.dispatch(
        applyDeltaAction({
          mutationId: 'mutation-1',
          updateWorkflow: { blockSlugs: ['block-2', 'block-1'] }
        })
      )
      // Optimistic update is gone: the real update took its place
      expect(store.getState().pendingMutations).toEqual([])
      expect(selectReport(store.getState())).toEqual(expectedReport)
    })

    it('should expand auto-report before reorder', async () => {
      let endDelay
      const delay = new Promise((resolve, reject) => {
        endDelay = resolve
      })
      const api = {
        reorderBlocks: jest.fn(() => delay)
      }
      const step1 = { slug: 'step-1', module: 'chart' }
      const step2 = { slug: 'step-2', module: 'chart' }
      const store = mockStore(
        {
          workflow: {
            hasCustomReport: false,
            blockSlugs: [],
            tab_slugs: ['tab-1']
          },
          tabs: {
            'tab-1': { step_ids: [1, 2] }
          },
          steps: { 1: step1, 2: step2 },
          modules: {
            chart: { has_html_output: true }
          },
          blocks: {},
          selectedPane: {}
        },
        api
      )

      const expectedReport = [
        { slug: 'block-auto-step-2', type: 'chart', step: step2 },
        { slug: 'block-auto-step-1', type: 'chart', step: step1 }
      ]

      generateSlug.mockImplementation(prefix => prefix + '1')
      const done = store.dispatch(
        actions.reorderBlocks(['block-auto-step-2', 'block-auto-step-1'])
      )
      expect(api.reorderBlocks).toHaveBeenCalledWith({
        mutationId: 'mutation-1',
        slugs: ['block-auto-step-2', 'block-auto-step-1']
      })

      expect(store.getState().pendingMutations.map(u => u.id)).toEqual([
        'mutation-1'
      ])
      expect(
        selectOptimisticState(store.getState()).workflow.hasCustomReport
      ).toBe(true)
      expect(selectReport(store.getState())).toEqual(expectedReport)

      endDelay()
      await done
      // Optimistic update is still there
      expect(store.getState().pendingMutations.map(u => u.id)).toEqual([
        'mutation-1'
      ])
      expect(
        selectOptimisticState(store.getState()).workflow.hasCustomReport
      ).toBe(true)
      expect(selectReport(store.getState())).toEqual(expectedReport)

      await store.dispatch(
        applyDeltaAction({
          mutationId: 'mutation-1',
          updateWorkflow: {
            hasCustomReport: true,
            blockSlugs: ['block-auto-step-2', 'block-auto-step-1']
          },
          updateBlocks: {
            'block-auto-step-1': { type: 'chart', stepSlug: 'step-1' },
            'block-auto-step-2': { type: 'chart', stepSlug: 'step-2' }
          },
          selectedPane: {}
        })
      )
      // Optimistic update is gone: the real update took its place
      expect(store.getState().pendingMutations).toEqual([])
      expect(selectReport(store.getState())).toEqual(expectedReport)
      expect(
        selectOptimisticState(store.getState()).workflow.hasCustomReport
      ).toBe(true)
    })
  })

  describe('setBlockMarkdown', () => {
    it('should call api.setBlockMarkdown', async () => {
      let endDelay
      const delay = new Promise((resolve, reject) => {
        endDelay = resolve
      })
      const api = {
        setBlockMarkdown: jest.fn(() => delay)
      }
      const store = mockStore(
        {
          workflow: {
            hasCustomReport: true,
            blockSlugs: ['block-1']
          },
          blocks: {
            'block-1': { type: 'text', markdown: 'foo' }
          },
          selectedPane: {}
        },
        api
      )

      generateSlug.mockImplementation(prefix => prefix + '1')
      const done = store.dispatch(actions.setBlockMarkdown('block-1', 'bar'))
      expect(api.setBlockMarkdown).toHaveBeenCalledWith({
        mutationId: 'mutation-1',
        slug: 'block-1',
        markdown: 'bar'
      })

      expect(store.getState().pendingMutations.map(u => u.id)).toEqual([
        'mutation-1'
      ])
      expect(
        selectOptimisticState(store.getState()).blocks['block-1'].markdown
      ).toEqual('bar')

      endDelay()
      await done
      // Optimistic update is still there
      expect(store.getState().pendingMutations.map(u => u.id)).toEqual([
        'mutation-1'
      ])
      expect(
        selectOptimisticState(store.getState()).blocks['block-1'].markdown
      ).toEqual('bar')

      await store.dispatch(
        applyDeltaAction({
          mutationId: 'mutation-1',
          updateBlocks: { 'block-1': { type: 'text', markdown: 'bar' } }
        })
      )
      // Optimistic update is gone: the real update took its place
      expect(store.getState().pendingMutations).toEqual([])
      expect(
        selectOptimisticState(store.getState()).blocks['block-1'].markdown
      ).toEqual('bar')
    })

    // Fiddle with console.warn because workflowReducer logs on unhandled error
    const originalWarn = console.warn
    beforeEach(() => {
      global.console.warn = jest.fn()
    })
    afterEach(() => {
      global.console.warn = originalWarn
    })

    it('should revert optimistic mutation on error', async () => {
      const api = {
        setBlockMarkdown: jest.fn(() => Promise.reject(new Error('failed')))
      }
      const store = mockStore(
        {
          workflow: {
            hasCustomReport: true,
            blockSlugs: ['block-1']
          },
          blocks: {
            'block-1': { type: 'text', markdown: 'foo' }
          },
          selectedPane: {}
        },
        api
      )

      const done = store.dispatch(actions.setBlockMarkdown('block-1', 'bar'))
      expect(
        selectOptimisticState(store.getState()).blocks['block-1'].markdown
      ).toEqual('bar') // applied
      await done
      expect(store.getState().pendingMutations).toEqual([])
      expect(
        selectOptimisticState(store.getState()).blocks['block-1'].markdown
      ).toEqual('foo') // unapplied because error
    })
  })
})
