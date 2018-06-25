import React from 'react'
import { mount } from 'enzyme'
import { jsonResponseMock } from './test-utils';
import TableView, { initialRows, preloadRows, deltaRows } from './TableView';
import DataGrid from './DataGrid';

jest.mock('./EditCells');
jest.mock('./SortFromTable');
jest.mock('./ReorderColumns');
import { addCellEdit } from './EditCells';
import { updateSort } from './SortFromTable';
import { updateReorder } from './ReorderColumns';

describe('TableView', () => {
  const defaultProps = {
    resizing: false,
    showColumnLetter: false,
    isReadOnly: false,
  }

  beforeEach(() => {
    addCellEdit.mockReset()
    updateSort.mockReset()
    updateReorder.mockReset()
  })

  // Mocks json response (promise) returning part of a larger table
  function makeRenderResponse(start, end, totalRows) {
    let nRows = end-start;
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


  it('Fetches, renders, edits cells, sorts columns and reorders columns', (done) => {
    var api = {
      render: makeRenderResponse(0, 2, 1000)
    };

    const tree = mount(
      <TableView {...defaultProps} selectedWfModuleId={100} revision={1} api={api} isReadOnly={false}/>
    )

    // wait for promise to resolve, then see what we get
    setImmediate(() => {
      // should have called API for its data, and loaded it
      expect(api.render).toHaveBeenCalledWith(100, 0, initialRows);

      expect(tree).toMatchSnapshot();

      // Header etc should be here
      expect(tree.find('.outputpane-header')).toHaveLength(1);
      expect(tree.find('.outputpane-data')).toHaveLength(1);

      // Row count should have a comma
      let headerText = tree.find('.outputpane-header').text();
      expect(headerText).toContain('1,000');  

      // Test calls to EditCells.addCellEdit
      // Don't call addCellEdit if the cell value has not changed
      tree.find(TableView).instance().onEditCell(0, 'c', '3');
      expect(addCellEdit).not.toHaveBeenCalled();
      // Do call addCellEdit if the cell value has changed
      tree.find(TableView).instance().onEditCell(1, 'b', '1000');
      expect(addCellEdit).toHaveBeenCalledWith(100, { row: 1, col: 'b', value: '1000' });

      // Calls SortFromTable
      tree.find(TableView).instance().onSort('a', 'Number');
      expect(updateSort).toHaveBeenCalledWith(100, 'a', 'Number');

      // Calls ReorderColumns
      tree.find(DataGrid).instance().onDropColumnIndexAtIndex(0, 1);
      expect(updateReorder).toHaveBeenCalledWith(100, { column: 'a', from: 0, to: 1 });

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

  it('Lazily loads rows as needed', (done) => {

    expect(deltaRows).toBeGreaterThan(preloadRows); // or preload logic breaks

    const totalRows = 100000;
    var api = {
      render: makeRenderResponse(0, initialRows, totalRows) // response to expected first call
    };

    const tree = mount(
      <TableView {...defaultProps} selectedWfModuleId={100} revision={1} api={api} isReadOnly={false}/>
    );
    let tableView = tree.find('TableView').instance();

    // Should load 0..initialRows at first
    expect(api.render).toHaveBeenCalledWith(100, 0, initialRows);

    // let rows load
    setImmediate(() => {

      // force load by reading past initialRows
      let requestRow = initialRows + 1;
      let lastLoadedRow = requestRow + deltaRows + preloadRows;
      api.render = makeRenderResponse(initialRows, lastLoadedRow, totalRows);
      let row = tableView.getRow(requestRow);

      // a row we haven't loaded yet should be blank
      expect(row).toEqual(tableView.emptyRow());

      expect(api.render.mock.calls.length).toBe(1);
      expect(api.render.mock.calls[0][1]).toBe(initialRows);
      expect(api.render.mock.calls[0][2]).toBe(lastLoadedRow);

      // let rows load
      setImmediate(() => {

        // Call getRow twice without waiting for the first load to finish, and ensure
        // the next getRow fetches up to the high water mark
        let requestRow2 = lastLoadedRow + 1;
        let lastLoadedRow2 = requestRow2 + deltaRows + preloadRows;
        api.render = makeRenderResponse(lastLoadedRow, lastLoadedRow2, totalRows);
        row = tableView.getRow(requestRow2);
        expect(row).toEqual(tableView.emptyRow());
        expect(tableView.loading).toBe(true);
        expect(api.render.mock.calls.length).toBe(1);
        expect(api.render.mock.calls[0][1]).toBe(lastLoadedRow);
        expect(api.render.mock.calls[0][2]).toBe(lastLoadedRow2);

        let requestRow3 = Math.floor(totalRows / 2);  // thousands of rows later
        row = tableView.getRow(requestRow3);
        expect(row).toEqual(tableView.emptyRow());
        expect(api.render.mock.calls.length).toBe(1);   // already loading, should not have started a new load

        setImmediate(() => {
          expect(tableView.loading).toBe(false);

          // Now start yet another load, for something much smaller that requestRow3
          let requestRow4 = lastLoadedRow2 + 1;                         // ask for very next unloaded row...
          let lastLoadedRow3 = requestRow3 + deltaRows + preloadRows;  // ...but should end up loading much more
          api.render = makeRenderResponse(lastLoadedRow2, lastLoadedRow3, totalRows);
          tableView.getRow(requestRow4);
          expect(api.render.mock.calls.length).toBe(1);
          expect(api.render.mock.calls[0][1]).toBe(lastLoadedRow2);
          expect(api.render.mock.calls[0][2]).toBe(lastLoadedRow3);

          setImmediate( ()=> {
            expect(tableView.loading).toBe(false);

            // Load to end
            let requestRow5 = totalRows-1;
            api.render = makeRenderResponse(lastLoadedRow3, totalRows, totalRows);
            row = tableView.getRow(requestRow5);
            expect(row).toEqual(tableView.emptyRow());
            expect(api.render.mock.calls.length).toBe(1);
            expect(api.render.mock.calls[0][1]).toBe(lastLoadedRow3);
            expect(api.render.mock.calls[0][2]).toBeGreaterThanOrEqual(totalRows);

            setImmediate(() =>{
              expect(tableView.loading).toBe(false);

              // Now that we've loaded the whole table, asking for the last row should not trigger a render
              api.render = jsonResponseMock({});
              row = tableView.getRow(totalRows-1);
              expect(row.a).toBe('1'); // not empty
              expect(api.render.mock.calls.length).toBe(0); // no new calls

              done();
            })
          })
        })
      })
    })

  });

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
          sortDirection={'DESC'}
      />
    );

    setImmediate(() => {
      tree.update();
      const dataGrid = tree.find(DataGrid);
      expect(dataGrid.prop('sortColumn')).toBe('b');
      expect(dataGrid.prop('sortDirection')).toBe('DESC');
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


