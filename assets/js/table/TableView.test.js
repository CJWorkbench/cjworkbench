/* global describe, it, expect, jest */
import React from 'react'
import { mount } from 'enzyme'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import { jsonResponseMock, sleep, tick } from '../test-utils'
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

  const wrapper = (extraProps={}) => {
    // mock store for <SelectedRowsActions>, a descendent
    store = mockStore({ modules: {}, workflow: { wf_modules: [ 99, 100, 101 ] } })

    return mount(
      <ConnectedTableView
        store={store}
        showColumnLetter={false}
        isReadOnly={false}
        selectedWfModuleId={100}
        lastRelevantDeltaId={1}
        {...extraProps}
      />
    )
  }

  beforeEach(() => {
    updateTableActionModule.mockReset()
  })

  // Mocks json response (promise) returning part of a larger table
  function makeRenderResponse (start, end, totalRows) {
    let nRows = end - start - 1
    let data = {
      total_rows: totalRows,
      start_row: start,
      end_row: end,
      columns: ["a", "b", "c"],
      column_types: ["Number", "Number", "Number"],
      rows: Array(nRows).fill({ a: 1, b: 2, c: 3 })
    }
    return jsonResponseMock(data)
  }


  it('Fetches, renders, edits cells, sorts columns, reorders columns, duplicates column', async () => {
    const api = { render: makeRenderResponse(0, 3, 1000) }
    const tree = wrapper({ api })

    await tick() // let rows load

    // should have called API for its data, and loaded it
    expect(api.render).toHaveBeenCalledWith(100, 0, NRowsPerPage + 1)

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
    const tree = wrapper({ selectedWfModuleId: undefined, api: {} })
    expect(tree.find('.outputpane-header')).toHaveLength(1)
    expect(tree.find('.outputpane-data')).toHaveLength(1)
    // And we can see it did not call api.render, because that does not exist
  })

  it('lazily loads rows as needed', async () => {
    const totalRows = 100000
    const api = {
      render: makeRenderResponse(0, 201, totalRows) // response to expected first call
    }

    const tree = wrapper({ api })

    // Should load 0..initialRows at first
    expect(api.render).toHaveBeenCalledWith(100, 0, 201)

    await tick() // let rows load

    // force load by reading past initialRows
    api.render = makeRenderResponse(412, 613, totalRows)
    const row = tree.find(TableView).instance().getRow(412)

    // a row we haven't loaded yet should be blank
    expect(row).toEqual({ '': '', ' ': '', '  ': '', '   ': '' })

    // Be careful about a race in this test. We've _started_ a timeout of
    // FetchTimeout ms, but if we simply schedule another timeout for
    // (FetchTimeout+1)ms, we risk the second timeout happening before the
    // first. We can make the race _far_ less likely to stimy us by sleeping
    // _after_ the initial FetchTimeout ms are done.
    await sleep(FetchTimeout) // executes the next line around the same time as api.render()
    await sleep(4) // makes sure the next line comes _after_ api.render()

    expect(api.render).toHaveBeenCalledWith(100, 412, 613)
  })

  it('keeps previous rows when loading new rows', async () => {
    const data1 = {
      total_rows: 2,
      start_row: 0,
      end_row: 2,
      columns: [ 'A', 'B' ],
      column_types: [ 'Number', 'Number' ],
      rows: [
        { A: 1, B: 2 },
        { A: 3, B: 4 }
      ]
    }

    const data2 = {
      ...data1,
      columns: [ 'C', 'D' ],
      rows: [
        { C: 5, D: 6 },
        { C: 7, D: 8 }
      ]
    }

    const render = jest.fn()
      .mockReturnValueOnce(Promise.resolve(data1))
      .mockReturnValueOnce(Promise.resolve(data2))

    const api = { render }

    const tree = wrapper({ api })
    await tick()

    expect(tree.text()).toMatch(/JSON FEED.*A.*B/)
    expect(tree.text()).toMatch(/3.*4/)

    // Select the last row
    tree.find('input[name="row-selected-1"]').simulate('change', { target: { checked: true } })
    tree.update()
    expect(tree.find('.react-grid-Row.row-selected')).toHaveLength(1)

    tree.setProps({
      selectedWfModuleId: 101,
      lastRelevantDeltaId: 2
    })
    tree.update()
    // Previous data remains
    expect(tree.text()).toMatch(/A.*B/)
    expect(tree.text()).toMatch(/3.*4/)
    expect(tree.find('#spinner-container-transparent')).toHaveLength(1)
    // ... except the selection, which is gone
    expect(tree.find('.react-grid-Row.row-selected')).toHaveLength(0)

    await tick()
    tree.update()

    // Now it's new data
    expect(tree.find('#spinner-container-transparent')).toHaveLength(0)
    expect(tree.text()).not.toMatch(/A.*B/)
    expect(api.render).toHaveBeenCalledWith(101, 0, 201)
    expect(tree.text()).toMatch(/JSON FEED.*C.*D/)
    expect(tree.text()).toMatch(/5.*7/)
    // ... and the selection is still gone
    expect(tree.find('.react-grid-Row.row-selected')).toHaveLength(0)
  })

  it('passes the the right sortColumn, sortDirection to DataGrid', async () => {
    const testData = {
      total_rows: 2,
      start_row: 0,
      end_row: 2,
      columns: ["a", "b", "c"],
      rows: [
        { a: 1, b: 2, c: 3 },
        { a: 4, b: 5, c: 6 }
      ],
      column_types: ['Number', 'Number', 'Number']
    }

    const api = { render: jsonResponseMock(testData) }

    // Try a mount with the sort module selected, should have sortColumn and sortDirection
    const tree = wrapper({
      api,
      sortColumn: 'b',
      sortDirection: sortDirectionDesc
    })

    await tick() // wait for rows to load
    tree.update()
    const dataGrid = tree.find(DataGrid)
    expect(dataGrid.prop('sortColumn')).toBe('b')
    expect(dataGrid.prop('sortDirection')).toBe(sortDirectionDesc)
  })

  it('shows a spinner on initial load', async () => {
    const testData = {
      total_rows: 2,
      start_row: 0,
      end_row: 2,
      columns: ["a", "b", "c"],
      rows: [
        { a: 1, b: 2, c: 3 },
        { a: 4, b: 5, c: 6 }
      ],
      column_types: ['Number', 'Number', 'Number']
    }

    const api = { render: jsonResponseMock(testData) }
    const tree = wrapper({ api })

    expect(tree.find('#spinner-container-transparent')).toHaveLength(1)
    await tick()
    tree.update()
    expect(tree.find('#spinner-container-transparent')).toHaveLength(0)
  })

  it('passes the the right showLetter prop to DataGrid', async () => {
    const testData = {
      total_rows: 2,
      start_row: 0,
      end_row: 2,
      columns: ["a", "b", "c"],
      rows: [
        { a: 1, b: 2, c: 3 },
        { a: 4, b: 5, c: 6 }
      ],
      column_types: ['Number', 'Number', 'Number']
    }

    const api = { render: jsonResponseMock(testData) }
    const tree = wrapper({ api, showColumnLetter: true })

    await tick() // wait for rows to load
    tree.update()
    const dataGrid = tree.find(DataGrid)
    expect(dataGrid).toHaveLength(1)
    expect(dataGrid.prop('showLetter')).toBe(true)
  })
  it('should not allow more than 100 columns to display', async () => {
    let testData = {
      total_rows: 2,
      start_row: 0,
      end_row: 2,
      columns: [...Array(NMaxColumns + 1).keys()],
      rows: [
        { a: 1, b: 2, c: 3 },
        { a: 4, b: 5, c: 6 }
      ],
      column_types: ['Number', 'Number', 'Number']
    }

    const api = { render: jsonResponseMock(testData) }
    const tree = wrapper({api, showColumnLetter: true })

    await tick() // wait for rows to load
    tree.update()
    const overlay = tree.find('.overlay')
    expect(overlay).toHaveLength(1)
  })
})
