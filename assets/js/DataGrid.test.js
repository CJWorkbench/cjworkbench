import React from 'react'
import { mount } from 'enzyme'
import DataGrid from "./DataGrid"

it('Renders the grid', () => {

  var testData = {
    totalRows : 2,
    columns : ["aaa", "bbbb", "ccccc"],
    rows : [
      {
      "aaa": "1",
      "bbbb": "foo",
      "ccccc": "3"
      },
      {
      "aaa": "4",
      "bbbb": "5",
      "ccccc": "baz"
      }
    ]
  };

  function getRow(i) {
//    console.log('getting row ' + str(i));
    return testData.rows[i];
  }

  var editCellMock = jest.fn();

  const tree = mount( <DataGrid
    totalRows={testData.totalRows}
    columns={testData.columns}
    getRow={getRow}
    onEditCell={editCellMock}
  />);

  // Check that we ended up with four columns (first is row number), with the right names
  // If rows values are not present, ensure intial DataGrid state.gridHeight > 0
  expect(tree.find('HeaderCell')).toHaveLength(4);
  let text = tree.text();
  expect(text).toContain('aaa');
  expect(text).toContain('bbbb');
  expect(text).toContain('ccccc');
  expect(text).toContain('foo');

  expect(tree).toMatchSnapshot();

  // Double click on a cell, enter text, enter, and ensure onCellEdit is called
  // Sadly, can't get this to work
  // var cell = tree.find('Cell').first();
  // expect(cell).toHaveLength(1)
  // cell.simulate('doubleclick');
  // cell.simulate('keydown', { which: 'X' });
  // cell.simulate('keydown', { which: '\n' });
  // expect(editCellMock.mock.calls).toHaveLength(1);
});


it('Render without data', () => {

  const tree = mount( <DataGrid
    totalRows={0}
    columns={[]}
    getRow={() => {}}
  />);
  expect(tree.find('HeaderCell')).toHaveLength(0);

  expect(tree).toMatchSnapshot();
});


