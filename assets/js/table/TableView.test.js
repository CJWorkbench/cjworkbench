/* global beforeEach, describe, it, expect, jest */
import '../__mocks__/ResizeObserver'
import { act } from 'react-dom/test-utils'
import { mountWithI18n } from '../i18n/test-utils'
import { Provider } from 'react-redux'
import { mockStore, tick } from '../test-utils'
import { generateSlug } from '../utils'
import ConnectedTableView from './TableView'

jest.mock('../utils')

global.fetch = jest.fn(() => Promise.reject(new Error('Mock me')))
beforeEach(() => global.fetch.mockClear())

/*
 * Help BigTable/Viewport.js calculate the wanted parts of the table.
 *
 * These are globals! They apply to all tests in this file.
 *
 * <th> -- has width=60, height=30; also, has a non-null .offsetParent
 * <div> (viewport) -- has width=650, height=200
 *
 * Each non-header cell has width=180. That's a magic number somewhere....
 */
global.HTMLTableCellElement.prototype.getBoundingClientRect = () => (
  { width: 60, height: 30 }
)
Object.defineProperty(global.HTMLTableCellElement.prototype, 'offsetParent', {
  get () { return 'not null' }
})
Object.defineProperty(global.HTMLDivElement.prototype, 'offsetWidth', {
  get () { return 650 }
})
Object.defineProperty(global.HTMLDivElement.prototype, 'offsetHeight', {
  get () { return 1000 }
})

class MockHttpResponse {
  constructor (status, json) {
    this.status = status
    this.ok = this.status >= 200 && this.status < 300
    this.json = () => Promise.resolve(json)
  }
}

describe('TableView', () => {
  const wrapper = (store, extraProps = {}) => {
    // mock store for <SelectedRowsActions>, a descendent
    if (store === null) {
      store = mockStore({
        settings: {
          bigTableColumnsPerTile: 4,
          bigTableRowsPerTile: 5
        },
        modules: {},
        workflow: {
          steps: [99, 100, 101]
        }
      })
    }

    return mountWithI18n(
      <Provider store={store}>
        <ConnectedTableView
          isReadOnly={false}
          workflowIdOrSecretId='w123'
          stepSlug='step-1'
          stepId={100}
          deltaId={2}
          status='ok'
          columns={[
            { name: 'A', type: 'text' },
            { name: 'B', type: 'text' },
            { name: 'C', type: 'text' }
          ]}
          nRows={0}
          {...extraProps}
        />
      </Provider>
    )
  }

  it('reorders columns', async () => {
    // integration-test style -- these moving parts tend to rely on one another
    // lots: ignoring workflow-reducer means tests miss bugs.
    const api = { addStep: jest.fn(() => Promise.resolve(null)) }
    generateSlug.mockImplementationOnce(prefix => prefix + 'X')
    const store = mockStore(
      {
        settings: {
          bigTableColumnsPerTile: 4,
          bigTableRowsPerTile: 5
        },
        workflow: {
          tab_slugs: ['tab-1']
        },
        tabs: {
          'tab-1': { step_ids: [2, 3], selected_step_position: 0 }
        },
        steps: {
          2: { slug: 'step-2', tab_slug: 'tab-1' },
          3: {}
        },
        modules: {
          reordercolumns: {}
        }
      },
      api
    )

    const tree = wrapper(store, { stepSlug: 'step-2', stepId: 2 })
    tree
      .find('DataGrid')
      .instance()
      .handleDropColumnIndexAtIndex(0, 2)

    await tick()

    expect(api.addStep).toHaveBeenCalledWith(
      'tab-1',
      'step-X',
      'reordercolumns',
      1,
      {
        'reorder-history': JSON.stringify([{ column: 'a', to: 1, from: 0 }])
      }
    )

    await tick() // let things settle
  })

  it('edits cells', async () => {
    // integration-test style -- these moving parts tend to rely on one another
    // lots: ignoring workflow-reducer means tests miss bugs.
    const api = {
      addStep: jest.fn().mockImplementation(() => Promise.resolve(null))
    }
    generateSlug.mockImplementationOnce(prefix => prefix + 'X')
    const store = mockStore(
      {
        settings: {
          bigTableColumnsPerTile: 4,
          bigTableRowsPerTile: 5
        },
        workflow: {
          tab_slugs: ['tab-1']
        },
        tabs: {
          'tab-1': { step_ids: [2, 3], selected_step_position: 0 }
        },
        steps: {
          2: { slug: 'step-2', tab_slug: 'tab-1' },
          3: {}
        },
        modules: {
          editcells: {}
        }
      },
      api
    )

    const tree = wrapper(store, { stepSlug: 'step-2', stepId: 2 })
    await tick() // load data
    tree
      .find('DataGrid')
      .instance()
      .handleGridRowsUpdated({
        fromRow: 0,
        fromRowData: { a: 'a1', b: 'b1', c: 'c1' },
        toRow: 0,
        cellKey: 'b',
        updated: { b: 'b2' }
      })

    expect(api.addStep).toHaveBeenCalledWith(
      'tab-1',
      'step-X',
      'editcells',
      1,
      {
        celledits: [{ row: 0, col: 'b', value: 'b2' }]
      }
    )

    await tick() // let things settle
  })

  // TODO move this to TableSwitcher.js/DelayedTableSwitcher.js:
  // it('shows a spinner on initial load', async () => {
  //  const testData = {
  //    start_row: 0,
  //    end_row: 2,
  //    rows: [
  //      { a: 1, b: 2, c: 3 },
  //      { a: 4, b: 5, c: 6 }
  //    ]
  //  }

  //  const tree = wrapper(null, { loadData: jest.fn(() => Promise.resolve(testData)) })

  //  expect(tree.find('#spinner-container-transparent')).toHaveLength(1)
  //  await tick()
  //  tree.update()
  //  expect(tree.find('#spinner-container-transparent')).toHaveLength(0)
  // })

  it('should edit a cell', async () => {
    // Copy `testRows`: react-data-grid modifies things AARGH why do we still use it
    const tree = await wrapper(null)
    await tick()
    tree.update() // load data
    // weird incantation to simulate double-click
    tree.find('.react-grid-Cell').first().simulate('click')
    tree.find('.react-grid-Cell').first().simulate('doubleClick')
    const input = tree.find('EditorContainer')
    input.find('input').instance().value = 'X' // react-data-grid has a weird way of editing cells
    input.simulate('keyDown', { key: 'Enter' })
    expect(tree.find('DataGrid').prop('editCell')).toHaveBeenCalledWith(0, 'aaa', 'X')
  })

  it('should not edit a cell when its value does not change', async () => {
    const tree = await wrapper(null)
    await tick()
    tree.update() // load data
    // weird incantation to simulate double-click
    tree.find('.react-grid-Cell').first().simulate('click')
    tree.find('.react-grid-Cell').first().simulate('doubleClick')
    const input = tree.find('EditorContainer')
    input.simulate('keyDown', { key: 'Enter' })
    expect(tree.find('DataGrid').prop('editCell')).not.toHaveBeenCalled()
  })

  it('should select a row', async () => {
    global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
      rows: [
        ['a1', 'b1', 'c1'],
        ['b1', 'b2', 'b3']
      ]
    })))
    const tree = await wrapper(null, { nRows: 2 })
    await act(async () => await tick())
    expect(tree.find('input[type="checkbox"]').at(1).prop('value')).toBe(false)
    await act(async () => {
      tree.find('input[type="checkbox"]').at(1).simulate('click')
      await tick()
      tree.update()
    })
    expect(tree.find('input[type="checkbox"]').at(1).prop('value')).toBe(true)
  })
})
