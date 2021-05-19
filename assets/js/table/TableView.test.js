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
Object.defineProperty(global.HTMLDivElement.prototype, 'clientWidth', {
  get () { return 650 }
})
Object.defineProperty(global.HTMLDivElement.prototype, 'clientHeight', {
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

  it('should focus a row (not cell) when clicking the <th>', async () => {
    global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
      rows: [
        ['a1', 'b1', 'c1'],
        ['b1', 'b2', 'b3']
      ]
    })))
    const tree = await wrapper(null, { nRows: 2 })
    await act(async () => await tick())
    await act(async () => {
      // The focus happens on click, not mousedown: when shift-clicking to
      // select, the selection logic (which happens on click) inspects the
      // pre-setFocusCell() value.
      tree.find('input[type="checkbox"]').at(1).simulate('click')
      await tick()
      tree.update()
    })
    expect(tree.find('tbody th').at(1).prop('className')).toEqual('focus')
  })

  it('should clear selection when clicking a <td>', async () => {
    global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
      rows: [
        ['a1', 'b1', 'c1'],
        ['b1', 'b2', 'b3']
      ]
    })))
    const tree = await wrapper(null, { nRows: 2 })
    await act(async () => await tick())
    await act(async () => {
      tree.find('input[type="checkbox"]').at(1).simulate('click')
      await tick()
      tree.update()
    })
    await act(async () => {
      tree.find('tbody td').at(2).simulate('mousedown', { button: 0 })
      await tick()
      tree.update()
    })
    expect(tree.find('input[type="checkbox"]').at(1).prop('value')).toBe(false)
  })

  it('should focus a cell after tabbing in, using only the keyboard', async () => {
    // When we design a nice keyboard-usability feature, rewrite this sequence.
    // For now, we're merely testing that it is *possible* to focus with keyboard.
    global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
      rows: [
        ['a1', 'b1', 'c1'],
        ['b1', 'b2', 'b3']
      ]
    })))
    const tree = await wrapper(null, { nRows: 2 })
    await act(async () => await tick())
    await act(async () => {
      tree.find('tbody').at(0).simulate('keydown', { key: 'ArrowDown' })
      await tick()
      tree.find('tbody').at(0).simulate('keydown', { key: 'ArrowRight' })
    })
    tree.update()
    expect(tree.find('tbody td').at(0).prop('className')).toEqual('type-text focus')
  })

  it('should focus a row after tabbing in, using only the keyboard', async () => {
    // When we design a nice keyboard-usability feature, rewrite this sequence.
    // For now, we're merely testing that it is *possible* to focus with keyboard.
    global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
      rows: [
        ['a1', 'b1', 'c1'],
        ['b1', 'b2', 'b3']
      ]
    })))
    const tree = await wrapper(null, { nRows: 2 })
    await act(async () => await tick())
    await act(async () => {
      tree.find('tbody').at(0).simulate('keydown', { key: 'ArrowDown' })
    })
    tree.update()
    expect(tree.find('tbody th').at(0).prop('className')).toEqual('focus')
  })

  it('should focus a cell on mousedown', async () => {
    global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
      rows: [
        ['a1', 'b1', 'c1'],
        ['b1', 'b2', 'b3']
      ]
    })))
    const tree = await wrapper(null, { nRows: 2 })
    await act(async () => await tick())
    await act(async () => {
      tree.find('tbody td').at(4).simulate('mousedown', { button: 0 })
    })
    tree.update()
    expect(tree.find('tbody td').at(4).prop('className')).toEqual('type-text focus')
  })

  it('should focus 20 rows up/down on PageUp/PageDown', async () => {
    global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
      rows: [
        ['a1', 'b1', 'c1'],
        ['a2', 'b2', 'c2'],
        ['a3', 'b3', 'c3'],
        ['a4', 'b4', 'c4'],
        ['a5', 'b5', 'c5'],
        ['a6', 'b6', 'c6'],
        ['a7', 'b7', 'c7'],
        ['a8', 'b8', 'c8'],
        ['a9', 'b9', 'c9'],
        ['a10', 'b10', 'c10'],
        ['a11', 'b11', 'c11'],
        ['a12', 'b12', 'c12'],
        ['a13', 'b13', 'c13'],
        ['a14', 'b14', 'c14'],
        ['a15', 'b15', 'c15'],
        ['a16', 'b16', 'c16'],
        ['a17', 'b17', 'c17'],
        ['a18', 'b18', 'c18'],
        ['a19', 'b19', 'c19'],
        ['a20', 'b20', 'c20'],
        ['a21', 'b21', 'c21'],
        ['a22', 'b22', 'c22'],
        ['a23', 'b23', 'c23'],
        ['a24', 'b24', 'c24'],
        ['a25', 'b25', 'c25'],
        ['a26', 'b26', 'c26'],
        ['a27', 'b27', 'c27'],
      ]
    })))
    const tree = await wrapper(
      mockStore({ settings: { bigTableRowsPerTile: 50, bigTableColumnsPerTile: 5 } }),
      { nRows: 27 }
    )
    await act(async () => await tick()) // load data
    await act(async () => {
      tree.find('tbody td').at(0).simulate('mousedown', { button: 0 })
    })
    await act(async () => {
      tree.find('tbody').simulate('keydown', { key: 'PageDown' })
    })
    tree.update()
    expect(tree.find('tbody td').at(60).prop('className')).toEqual('type-text focus')
    await act(async () => {
      tree.find('tbody').simulate('keydown', { key: 'ArrowDown' })
      await tick()
      tree.find('tbody').simulate('keydown', { key: 'PageUp' })
      tree.update()
    })
    expect(tree.find('tbody td').at(3).prop('className')).toEqual('type-text focus')
  })
})
