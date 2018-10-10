/* global describe, it, expect, jest */
import React from 'react'
import { mount } from 'enzyme'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import { sleep, tick } from '../test-utils'
import TableView, { NRowsPerPage, FetchTimeout, NMaxColumns } from './TableView'
import DataGrid from './DataGrid'

jest.mock('./UpdateTableAction')
import { sortDirectionAsc, sortDirectionDesc, sortDirectionNone, updateTableActionModule } from './UpdateTableAction'

// Ugly hack - let us setProps() on the mounted component
// See https://github.com/airbnb/enzyme/issues/947
//
// The problem is: we _must_ use mount() and not shallow() because we want to
// test TableView's componentDidMount() behavior (the loading of data). And
// since one of TableView's descendents uses react-redux, we must use a
// <Provider> to make mount() succeed.
//
// We want to test setProps(), because we do things when props change. But
// mounted components' setProps() only work on the root component.
//
// So here's a root component that handles setProps() and the <Provider>, all
// in one.
function ConnectedTableView (props) {
  props = { ...props } // clone
  const store = props.store
  delete props.store

  return (
    <Provider store={store}>
      <TableView {...props} />
    </Provider>
  )
}

describe('TableView', () => {
  const mockStore = configureStore()
  let store

  const wrapper = (extraProps={}, wfModuleProps={}) => {
    // mock store for <SelectedRowsActions>, a descendent
    store = mockStore({
      modules: {},
      workflow: {
        wf_modules: [ 99, 100, 101 ]
      }
    })

    return mount(
      <ConnectedTableView
        store={store}
        showColumnLetter={false}
        isReadOnly={false}
        wfModuleId={100}
        deltaId={1}
        onLoadPage={jest.fn()}
        columns={[
          { name: 'a', type: 'number' },
          { name: 'b', type: 'number' },
          { name: 'c', type: 'number' }
        ]}
        nRows={2}
        {...extraProps}
      />
    )
  }

  beforeEach(() => {
    updateTableActionModule.mockReset()
  })

  // Mocks json response (promise) returning part of a larger table
  function makeRenderResponse (start, end, totalRows) {
    const nRows = end - start - 1
    const data = {
      start_row: start,
      end_row: end,
      rows: Array(nRows).fill({ a: 1, b: 2, c: 3 })
    }
    return jest.fn(() => Promise.resolve(data))
  }

  it('Fetches, renders, edits cells, sorts columns, reorders columns, duplicates column', async () => {
    const api = { render: makeRenderResponse(0, 3, 1000) }
    const tree = wrapper({ api, nRows: 1000 })

    await tick(); tree.update() // let rows load

    // should have called API for its data, and loaded it
    expect(api.render).toHaveBeenCalledWith(100, 0, 200)

    // Header etc should be here
    expect(tree.find('.outputpane-header')).toHaveLength(1)
    expect(tree.find('.outputpane-data')).toHaveLength(1)

    // Row count should have a comma
    let headerText = tree.find('.outputpane-header').text()
    expect(headerText).toContain('1,000');  

    // Test calls to UpdateTableAction
    //// Don't call updateTableActionModule if the cell value has not changed
    //tree.find(TableView).instance().onEditCell(0, 'c', '3')
    //expect(updateTableActionModule).not.toHaveBeenCalled()
    // Do call updateTableActionModule if the cell value has changed
    tree.find(TableView).instance().onEditCell(1, 'b', '1000')

    expect(updateTableActionModule).toHaveBeenCalledWith(100, 'editcells', false, { row: 1, col: 'b', value: '1000' })

    // Calls updateTableActionModule for sorting
    tree.find(TableView).instance().setDropdownAction('sort-from-table', false, {columnKey: 'a', sortType: 'Number', sortDirection: sortDirectionAsc})
    expect(updateTableActionModule).toHaveBeenCalledWith(100, 'sort-from-table', false, {columnKey: 'a', sortType: 'Number', sortDirection: sortDirectionAsc})

    // Calls updateTableActionModule for duplicating column
    tree.find(TableView).instance().setDropdownAction('duplicate-column', false, {columnKey: 'a'})
    expect(updateTableActionModule).toHaveBeenCalledWith(100, 'duplicate-column', false, {columnKey: 'a'})

    // Calls updateTableActionModule for filtering column
    tree.find(TableView).instance().setDropdownAction('filter', true, {columnKey: 'a'})
    expect(updateTableActionModule).toHaveBeenCalledWith(100, 'filter', true, {columnKey: 'a'})

    // Calls updateTableActionModule for drop column
    tree.find(TableView).instance().setDropdownAction('selectcolumns', false, {columnKey: 'a'})
    expect(updateTableActionModule).toHaveBeenCalledWith(100, 'selectcolumns', false, {columnKey: 'a'})

    // Calls updateTableActionModule for column reorder
    tree.find(DataGrid).instance().onDropColumnIndexAtIndex(0, 1)
    expect(updateTableActionModule).toHaveBeenCalledWith(100, 'reorder-columns', false, { column: 'a', from: 0, to: 1 })
  })

  it('blanks table when no module id', () => {
    const tree = wrapper({ wfModuleId: undefined, api: {} })
    expect(tree.find('.outputpane-header')).toHaveLength(1)
    expect(tree.find('.outputpane-data')).toHaveLength(1)
    // And we can see it did not call api.render, because that does not exist
  })

  // TODO move this to DataGrid.js:
  //it('shows a spinner on initial load', async () => {
  //  const testData = {
  //    start_row: 0,
  //    end_row: 2,
  //    rows: [
  //      { a: 1, b: 2, c: 3 },
  //      { a: 4, b: 5, c: 6 }
  //    ]
  //  }

  //  const api = { render: jest.fn(() => Promise.resolve(testData)) }
  //  const tree = wrapper({ api })

  //  expect(tree.find('#spinner-container-transparent')).toHaveLength(1)
  //  await tick()
  //  tree.update()
  //  expect(tree.find('#spinner-container-transparent')).toHaveLength(0)
  //})

  it('passes the the right showLetter prop to DataGrid', async () => {
    const testData = {
      start_row: 0,
      end_row: 2,
      rows: [
        { a: 1, b: 2, c: 3 },
        { a: 4, b: 5, c: 6 }
      ]
    }

    const api = { render: jest.fn(() => Promise.resolve(testData)) }
    const tree = wrapper({ api, showColumnLetter: true })

    await tick() // wait for rows to load
    tree.update()
    const dataGrid = tree.find(DataGrid)
    expect(dataGrid).toHaveLength(1)
    expect(dataGrid.prop('showLetter')).toBe(true)
  })

  it('renders a message (and no table) when >100 columns', async () => {
    // This is because react-data-grid is so darned slow to render columns
    const columns = []
    for (let i = 0; i < 101; i++) {
      columns[i] = { name: String(i), type: 'number' }
    }

    const api = { render: jest.fn() }
    const tree = wrapper({ api, columns })

    const overlay = tree.find('.overlay')
    expect(overlay).toHaveLength(1)
  })
})
