import React from 'react'
import { mount } from 'enzyme'
import DataGrid, {ColumnHeader, EditableColumnName} from './DataGrid'

describe('DataGrid tests,', () => {
  // Column names are chosen to trigger
  // https://github.com/adazzle/react-data-grid/issues/1269 and
  // https://github.com/adazzle/react-data-grid/issues/1270
  const testColumns = [ 'aaa', 'bbbb', 'getCell', 'select-row' ]
  const testColumnTypes = [ 'number', 'text', 'text', 'text' ]
  const testRows = [
    {
      'aaa': 9,
      'bbbb': 'foo',
      'getCell': '9', // deliberately try and trigger https://github.com/adazzle/react-data-grid/issues/1270
      'select-row': 'someval' // deliberately try and trigger https://github.com/adazzle/react-data-grid/issues/1269
    },
    {
      'aaa': 9,
      'bbbb': '',
      'getCell': 'baz',
      'select-row': 'someotherval'
    }
  ]

  const wrapper = (extraProps={}) => mount(
    <DataGrid
      wfModuleId={100}
      totalRows={testRows.length}
      columns={testColumns}
      columnTypes={testColumnTypes}
      getRow={(i) => testRows[i]}
      onEditCell={jest.fn()}
      onGridSort={jest.fn()}
      isReadOnly={false}
      selectedRowIndexes={[]}
      setDropdownAction={jest.fn()}
      onSetSelectedRowIndexes={jest.fn()}
      onReorderColumns={jest.fn()}
      onRenameColumn={jest.fn()}
      {...extraProps}
    />
  )

  it('Renders the grid', () => {
    const tree = wrapper()

    // Check that we ended up with five columns (first is row number), with the right names
    // If rows values are not present, ensure intial DataGrid state.gridHeight > 0
    expect(tree.find('HeaderCell')).toHaveLength(5)

    // We now test the headers separately
    expect(tree.find('EditableColumnName')).toHaveLength(4)
    expect(tree.find('EditableColumnName').get(0).props.columnKey).toBe('aaa')
    expect(tree.find('EditableColumnName').get(1).props.columnKey).toBe('bbbb')
    expect(tree.find('EditableColumnName').get(2).props.columnKey).toBe('getCell')
    expect(tree.find('EditableColumnName').get(3).props.columnKey).toBe('select-row')

    const text = tree.text()

    expect(text).toContain('foo') // some cell values
    expect(text).toContain('someval')

    expect(text).toContain('1') // row numbers
    expect(text).toContain('2')

    expect(tree).toMatchSnapshot()
  })

  it('should edit a cell', () => {
    const tree = wrapper()
    // weird incantation to simulate double-click
    tree.find('.react-grid-Cell').first().simulate('click')
    tree.find('.react-grid-Cell').first().simulate('doubleClick')
    const input = tree.find('EditorContainer')
    input.find('input').instance().value = 'X' // react-data-grid has a weird way of editing cells
    input.simulate('keyDown', { key: 'Enter' })
    expect(tree.prop('onEditCell')).toHaveBeenCalledWith(0, 'aaa', 'X')
  })

  it('should not edit a cell when its value does not change', () => {
    const tree = wrapper()
    // weird incantation to simulate double-click
    tree.find('.react-grid-Cell').first().simulate('click')
    tree.find('.react-grid-Cell').first().simulate('doubleClick')
    const input = tree.find('EditorContainer')
    input.simulate('keyDown', { key: 'Enter' })
    expect(tree.prop('onEditCell')).not.toHaveBeenCalled()
  })

  it('should match snapshot without data', () => {
    const tree = wrapper({ totalRows: 0 })
    expect(tree).toMatchSnapshot()
    expect(tree.find('HeaderCell')).toHaveLength(0)
  })

  it('should show letters in the header according to props', () => {
    const tree = wrapper({ showLetter: true })
    expect(tree.find('.column-letter')).toHaveLength(4)
    expect(tree.find('.column-letter').at(0).text()).toEqual('A')
    expect(tree.find('.column-letter').at(1).text()).toEqual('B')
    expect(tree.find('.column-letter').at(2).text()).toEqual('C')
    expect(tree.find('.column-letter').at(3).text()).toEqual('D')
	})

  it('should hide letters in the header according to props', () => {
    const tree = wrapper({ showLetter: false })
    expect(tree.find('.column-letter')).toHaveLength(0)
  })

  it('should call column rename upon editing a column header', () => {
    const tree = wrapper()

    expect(tree.find('EditableColumnName')).toHaveLength(4)
    // Tests rename on aaaColumn
    tree.find('EditableColumnName').first().simulate('click')
    tree.update()
    const input = tree.find('EditableColumnName input[value="aaa"]')
    input.simulate('change', { target: { value: 'aaaa' }})
    input.simulate('blur')

    expect(tree.prop('onRenameColumn')).toHaveBeenCalledWith(100, 'rename-columns', false, { prevName: 'aaa', newName: 'aaaa' })
  })

  it('should respect isReadOnly for rename columns', () => {
    const tree = wrapper({ isReadOnly: true })
    tree.find('EditableColumnName').first().simulate('click')
    tree.update()
    expect(tree.find('EditableColumnName input')).toHaveLength(0)
  })

  it('should set className to include type', () => {
    const tree = wrapper()
    expect(tree.find('.cell-text')).toHaveLength(6)
    expect(tree.find('.cell-number')).toHaveLength(2)
  })

  it('should display "null" for none types', () => {
    const tree = wrapper({ getRow: (i) => ({ aaa: null, bbbb: null, getCell: null, 'select-row': null }) })
    expect(tree.find('.cell-null')).toHaveLength(8)
  })

  it('should select a row', () => {
    const tree = wrapper()
    expect(tree.find('input[type="checkbox"]').at(1).prop('checked')).toBe(false)
    tree.find('input[type="checkbox"]').at(1).simulate('change', { target: { checked: true } })
    expect(tree.prop('onSetSelectedRowIndexes')).toHaveBeenCalledWith([1])
  })

  it('should deselect a row', () => {
    const tree = wrapper({ selectedRowIndexes: [ 1 ] })
    expect(tree.find('input[type="checkbox"]').at(1).prop('checked')).toBe(true)
    tree.find('input[type="checkbox"]').at(1).simulate('change', { target: { checked: false } })
    expect(tree.prop('onSetSelectedRowIndexes')).toHaveBeenCalledWith([])
  })
})
