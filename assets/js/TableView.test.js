/* global describe, it, expect, jest */
import React from 'react'
import { mount } from 'enzyme'
import { jsonResponseMock, sleep, tick } from './test-utils'
import TableView, { NRowsPerPage, FetchTimeout } from './TableView'
import DataGrid from './DataGrid'

jest.mock('./UpdateTableAction')
import { sortDirectionAsc, sortDirectionDesc, sortDirectionNone, updateTableActionModule } from './UpdateTableAction'

describe('TableView', () => {
  const defaultProps = {
    resizing: false,
    showColumnLetter: false,
    isReadOnly: false,
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
      rows: Array(nRows).fill({
        "a": '1',
        "b": '2',
        "c": '3',
      })
    }
    return jsonResponseMock(data)
  }


  it('Fetches, renders, edits cells, sorts columns, reorders columns, duplicates column', (done) => {
    const api = {
      render: makeRenderResponse(0, 3, 1000)
    }

    const tree = mount(
      <TableView {...defaultProps} selectedWfModuleId={100} lastRelevantDeltaId={1} api={api} isReadOnly={false}/>
    )

    // wait for promise to resolve, then see what we get
    setImmediate(() => {
      // should have called API for its data, and loaded it
      expect(api.render).toHaveBeenCalledWith(100, 0, NRowsPerPage + 1)

      // Header etc should be here
      expect(tree.find('.outputpane-header')).toHaveLength(1)
      expect(tree.find('.outputpane-data')).toHaveLength(1)

      // Row count should have a comma
      let headerText = tree.find('.outputpane-header').text()
      expect(headerText).toContain('1,000');  

      // Test calls to UpdateTableAction
      // Don't call updateTableActionModule if the cell value has not changed
      tree.instance().onEditCell(0, 'c', '3')
      expect(updateTableActionModule).not.toHaveBeenCalled()
      // Do call updateTableActionModule if the cell value has changed
      tree.instance().onEditCell(1, 'b', '1000')

      expect(updateTableActionModule).toHaveBeenCalledWith(100, 'editcells', false, { row: 1, col: 'b', value: '1000' })

      // Calls updateTableActionModule for sorting
      tree.instance().setDropdownAction('sort-from-table', false, {columnKey: 'a', sortType: 'Number', sortDirection: sortDirectionAsc})
      expect(updateTableActionModule).toHaveBeenCalledWith(100, 'sort-from-table', false, {columnKey: 'a', sortType: 'Number', sortDirection: sortDirectionAsc})

      // Calls updateTableActionModule for duplicating column
      tree.instance().setDropdownAction('duplicate-column', false, {columnKey: 'a'})
      expect(updateTableActionModule).toHaveBeenCalledWith(100, 'duplicate-column', false, {columnKey: 'a'})

      // Calls updateTableActionModule for filtering column
      tree.instance().setDropdownAction('filter', true, {columnKey: 'a'})
      expect(updateTableActionModule).toHaveBeenCalledWith(100, 'filter', true, {columnKey: 'a'})

      // Calls updateTableActionModule for drop column
      tree.instance().setDropdownAction('selectcolumns', false, {columnKey: 'a'})
      expect(updateTableActionModule).toHaveBeenCalledWith(100, 'selectcolumns', false, {columnKey: 'a'})

      // Calls updateTableActionModule for column reorder
      // TODO uncomment!
      // tree.find(DataGrid).instance().onDropColumnIndexAtIndex(0, 1)
      // expect(updateTableActionModule).toHaveBeenCalledWith(100, 'reorder-columns', false, { column: 'a', from: 0, to: 1 })

      done()
    })
  })

  it('blanks table when no module id', () => {
    const tree = mount(
      <TableView {...defaultProps} selectedWfModuleId={undefined} lastRelevantDeltaId={1} api={{}} isReadOnly={false}/>
    )
    tree.update()

    expect(tree.find('.outputpane-header')).toHaveLength(1)
    expect(tree.find('.outputpane-data')).toHaveLength(1)
  })

  it('lazily loads rows as needed', async () => {
    const totalRows = 100000
    const api = {
      render: makeRenderResponse(0, 201, totalRows) // response to expected first call
    }

    const wrapper = mount(
      <TableView
        {...defaultProps}
        selectedWfModuleId={100}
        lastRelevantDeltaId={1}
        api={api}
        isReadOnly={false}
      />
    )

    // Should load 0..initialRows at first
    expect(api.render).toHaveBeenCalledWith(100, 0, 201)

    await tick() // let rows load

    // force load by reading past initialRows
    api.render = makeRenderResponse(412, 613, totalRows)
    const row = wrapper.instance().getRow(412)

    // a row we haven't loaded yet should be blank
    expect(row).toEqual({ '': '', ' ': '', '  ': '', '   ': '' })

    await sleep(FetchTimeout + 1) // let rows load again
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
        { 'A': 1, 'B': 2 },
        { 'A': 3, 'B': 4 }
      ]
    }

    const data2 = {
      ...data1,
      columns: [ 'C', 'D' ],
      rows: [
        { 'C': 5, 'D': 6 },
        { 'C': 7, 'D': 8 }
      ]
    }

    const render = jest.fn()
      .mockReturnValueOnce(Promise.resolve(data1))
      .mockReturnValueOnce(Promise.resolve(data2))

    const api = { render }

    const wrapper = mount(
      <TableView
        {...defaultProps}
        selectedWfModuleId={100}
        lastRelevantDeltaId={1}
        api={api}
        isReadOnly={false}
      />
    )
    await tick()

    expect(wrapper.text()).toMatch(/JSON FEED.*A.*B/)
    expect(wrapper.text()).toMatch(/3.*4/)

    wrapper.setProps({
      selectedWfModuleId: 101,
      lastRelevantDeltaId: 2
    })
    wrapper.update()
    // Previous data remains
    expect(wrapper.text()).toMatch(/A.*B/)
    expect(wrapper.text()).toMatch(/3.*4/)

    await tick()
    wrapper.update()

    // Now it's new data
    expect(api.render).toHaveBeenCalledWith(101, 0, 201)
    expect(wrapper.text()).toMatch(/JSON FEED.*C.*D/)
    expect(wrapper.text()).toMatch(/5.*7/)
  })

  it('passes the the right sortColumn, sortDirection to DataGrid', (done) => {
    const testData = {
      total_rows: 2,
      start_row: 0,
      end_row: 2,
      columns: ["a", "b", "c"],
      rows: [
        {
          "a": "1",
          "b": "2",
          "c": "3"
        },
        {
          "a": "4",
          "b": "5",
          "c": "6"
        }
      ],
      column_types: ['Number', 'Number', 'Number']
    }

    const api = {
      render: jsonResponseMock(testData),
    }

    // Try a mount with the sort module selected, should have sortColumn and sortDirection
    const tree = mount(
      <TableView
          {...defaultProps}
          lastRelevantDeltaId={1}
          selectedWfModuleId={100}
          api={api}
          setBusySpinner={jest.fn()}
          isReadOnly={false}
          sortColumn={'b'}
          sortDirection={sortDirectionDesc}
      />
    )

    setImmediate(() => {
      tree.update()
      const dataGrid = tree.find(DataGrid)
      expect(dataGrid.prop('sortColumn')).toBe('b')
      expect(dataGrid.prop('sortDirection')).toBe(sortDirectionDesc)
      done()
    })
  })

  it('passes the the right showLetter prop to DataGrid', (done) => {
    const testData = {
      total_rows: 2,
      start_row: 0,
      end_row: 2,
      columns: ["a", "b", "c"],
      rows: [
        {
          "a": "1",
          "b": "2",
          "c": "3"
        },
        {
          "a": "4",
          "b": "5",
          "c": "6"
        }
      ],
      column_types: ['Number', 'Number', 'Number']
    }

    const api = {
      render: jsonResponseMock(testData),
    }

    const NON_SHOWLETTER_ID = 28
    const SHOWLETTER_ID = 135

    // Try a mount with the formula module selected, should show letter
    const tree = mount(
      <TableView
          {...defaultProps}
          showColumnLetter={true}
          lastRelevantDeltaId={1}
          selectedWfModuleId={100}
          api={api}
          setBusySpinner={jest.fn()}
      />
    )
    setImmediate(() => {
      tree.update()
      const dataGrid = tree.find(DataGrid)
      expect(dataGrid).toHaveLength(1)
      expect(dataGrid.prop('showLetter')).toBe(true)
      done()
    })
  })
})
