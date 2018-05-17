import React from 'react'
import { mount } from 'enzyme'
import DataGrid from "./DataGrid"

describe('DataGrid tests,', () => {
  var testData = {
    totalRows : 2,
    columns : ["aaa", "bbbb", "ccccc", "rn_"],
    rows : [
      {
      "aaa": "9",
      "bbbb": "foo",
      "ccccc": "9",       // use digits that will not appear in our row numbers, so we can test
      "rn_" : "someval"   // deliberately conflict with DataGrid's default row number column key
      },
      {
      "aaa": "9",
      "bbbb": "9",
      "ccccc": "baz",
      "rn_" : "someotherval"
      }
    ]
  };

  function getRow(i) {
    return testData.rows[i];
  }

  it('Renders the grid', () => {

    var editCellMock = jest.fn();
    var sortMock = jest.fn();

    const tree = mount( <DataGrid
      totalRows={testData.totalRows}
      columns={testData.columns}
      getRow={getRow}
      onEditCell={editCellMock}
      onGridSort={sortMock} // I tried but could not get this to work, similar to onEditCell
    />);

    // Check that we ended up with five columns (first is row number), with the right names
    // If rows values are not present, ensure intial DataGrid state.gridHeight > 0
    expect(tree.find('HeaderCell')).toHaveLength(5);
    let text = tree.text();
    expect(text).toContain('aaa');      // columns
    expect(text).toContain('bbbb');
    expect(text).toContain('ccccc');
    expect(text).toContain('rn_');

    expect(text).toContain('foo');      // some cell values
    expect(text).toContain('someval');

    expect(text).toContain('1');        // row numbers
    expect(text).toContain('2');

    // row number column should not have the same name as any of our cols
    expect(testData.columns.includes(tree.instance().rowNumKey)).toBeFalsy();

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

  it('Shows/hides letters in the header according to props', () => {
    const treeWithLetter = mount(<DataGrid
        totalRows={testData.totalRows}
        columns={testData.columns}
        getRow={getRow}
        showLetter={true}
    />);
    expect(treeWithLetter.find('.column-letter')).toHaveLength(testData.columns.length);
    expect(treeWithLetter.find('.column-letter').get(0).props.children).toEqual('A');
    expect(treeWithLetter.find('.column-letter').get(1).props.children).toEqual('B');
    expect(treeWithLetter.find('.column-letter').get(2).props.children).toEqual('C');
    expect(treeWithLetter.find('.column-letter').get(3).props.children).toEqual('D');

    const treeWithoutLetter = mount(<DataGrid
        totalRows={testData.totalRows}
        columns={testData.columns}
        getRow={getRow}
        showLetter={false}
    />);
    expect(treeWithoutLetter.find('.column-letter')).toHaveLength(0);
  });
});


