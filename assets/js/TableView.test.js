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
    };
    return jsonResponseMock(data);
  }


  it('Fetches, renders, edits cells, sorts columns, reorders columns, duplicates column', (done) => {
    var api = {
      render: makeRenderResponse(0, 3, 1000)
    };

    const tree = mount(
      <TableView {...defaultProps} selectedWfModuleId={100} revision={1} api={api} isReadOnly={false}/>
    )

    // wait for promise to resolve, then see what we get
    setImmediate(() => {
      // should have called API for its data, and loaded it
      expect(api.render).toHaveBeenCalledWith(100, 0, NRowsPerPage + 1);

      expect(tree).toMatchSnapshot();

      // Header etc should be here
      expect(tree.find('.outputpane-header')).toHaveLength(1);
      expect(tree.find('.outputpane-data')).toHaveLength(1);

      // Row count should have a comma
      let headerText = tree.find('.outputpane-header').text();
      expect(headerText).toContain('1,000');  

      // Test calls to UpdateTableAction
      // Don't call updateTableActionModule if the cell value has not changed
      tree.instance().onEditCell(0, 'c', '3');
      expect(updateTableActionModule).not.toHaveBeenCalled();
      // Do call updateTableActionModule if the cell value has changed
      tree.instance().onEditCell(1, 'b', '1000');

      expect(updateTableActionModule).toHaveBeenCalledWith(100, 'editcells', false, { row: 1, col: 'b', value: '1000' });

      // Calls updateTableActionModule for sorting
      tree.instance().setSortDirection('a', 'Number', sortDirectionAsc);
      expect(updateTableActionModule).toHaveBeenCalledWith(100, 'sort-from-table', false, 'a', 'Number', sortDirectionAsc);

      // Calls updateTableActionModule for duplicating column
      tree.instance().duplicateColumn('a');
      expect(updateTableActionModule).toHaveBeenCalledWith(100, 'duplicate-column', false, 'a');

      // Calls updateTableActionModule for filtering column
      tree.instance().filterColumn('a');
      expect(updateTableActionModule).toHaveBeenCalledWith(100, 'filter', true, 'a');

      // Calls updateTableActionModule for drop column
      tree.instance().dropColumn('a');
      expect(updateTableActionModule).toHaveBeenCalledWith(100, 'selectcolumns', false, 'a');

      // Calls updateTableActionModule for column reorder
      // TODO uncomment!
      // tree.find(DataGrid).instance().onDropColumnIndexAtIndex(0, 1);
      // expect(updateTableActionModule).toHaveBeenCalledWith(100, 'reorder-columns', false, { column: 'a', from: 0, to: 1 });

      done();
    });
  });


  it('Blank table when no module id', () => {
    const tree = mount(
      <TableView {...defaultProps} selectedWfModuleId={undefined} revision={1} api={{}} isReadOnly={false}/>
    );
    tree.update();

    expect(tree.find('.outputpane-header')).toHaveLength(1);
    expect(tree.find('.outputpane-data')).toHaveLength(1);
    expect(tree).toMatchSnapshot();
  });

  it('Lazily loads rows as needed', async () => {
    const totalRows = 100000
    var api = {
      render: makeRenderResponse(0, 201, totalRows) // response to expected first call
    }

    const wrapper = mount(
      <TableView
        {...defaultProps}
        selectedWfModuleId={100}
        revision={1}
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

  it('Passes the the right sortColumn, sortDirection to DataGrid', (done) => {
    var testData = {
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
    };

    var api = {
      render: jsonResponseMock(testData),
    };

    // Try a mount with the sort module selected, should have sortColumn and sortDirection
    var tree = mount(
      <TableView
          {...defaultProps}
          revision={1}
          selectedWfModuleId={100}
          api={api}
          setBusySpinner={jest.fn()}
          isReadOnly={false}
          sortColumn={'b'}
          sortDirection={sortDirectionDesc}
      />
    );

    setImmediate(() => {
      tree.update();
      const dataGrid = tree.find(DataGrid);
      expect(dataGrid.prop('sortColumn')).toBe('b');
      expect(dataGrid.prop('sortDirection')).toBe(sortDirectionDesc);
      done();
    });
  });

  it('Passes the the right showLetter prop to DataGrid', (done) => {
    var testData = {
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
    };

    var api = {
      render: jsonResponseMock(testData),
    };

    const NON_SHOWLETTER_ID = 28;
    const SHOWLETTER_ID = 135;

    // Try a mount with the formula module selected, should show letter
    var tree = mount(
      <TableView
          {...defaultProps}
          showColumnLetter={true}
          revision={1}
          selectedWfModuleId={100}
          api={api}
          setBusySpinner={jest.fn()}
      />
    );
    setImmediate(() => {
      tree.update();
      const dataGrid = tree.find(DataGrid);
      expect(dataGrid).toHaveLength(1);
      expect(dataGrid.prop('showLetter')).toBe(true);
      done();
    });
  });
});


