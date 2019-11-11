/* globals describe, expect, it, jest */
import React from 'react'
import { Provider } from 'react-redux'
import { mountWithI18n } from '../i18n/test-utils'
import { mockStore, tick } from '../test-utils'
import DataGrid from './DataGrid'

describe('DataGrid', () => {
  // Column names are chosen to trigger
  // https://github.com/adazzle/react-data-grid/issues/1269 and
  // https://github.com/adazzle/react-data-grid/issues/1270
  const testColumns = [
    { name: 'aaa', type: 'number', format: '{:,}' },
    { name: 'bbbb', type: 'text' },
    // deliberately try and trigger https://github.com/adazzle/react-data-grid/issues/1270
    { name: 'getCell', type: 'text' },
    // deliberately try and trigger https://github.com/adazzle/react-data-grid/issues/1269
    { name: 'select-row', type: 'text' }
  ]

  const testRows = {
    start_row: 0,
    end_row: 2,
    rows: [
      {
        aaa: 9,
        bbbb: 'foo',
        getCell: '9',
        'select-row': 'someval'
      },
      {
        aaa: 9,
        bbbb: '',
        getCell: 'baz',
        'select-row': 'someotherval'
      }
    ]
  }

  // mount() so we get componentDidMount, componentWillUnmount()
  const wrapper = async (extraProps = {}, httpResponses = [testRows]) => {
    const defaultLoadRows = jest.fn()
    for (const httpResponse of httpResponses) {
      defaultLoadRows.mockReturnValueOnce(Promise.resolve(httpResponse))
    }

    // mock store for <ColumnHeader>, a descendent
    const store = mockStore({ modules: {} })

    const nRows = httpResponses.reduce((s, j) => s + j.rows.length, 0)

    const ret = mountWithI18n(
      <Provider store={store}>
        <DataGrid
          loadRows={defaultLoadRows}
          isReadOnly={false}
          wfModuleId={1}
          deltaId={2}
          columns={testColumns}
          nRows={nRows}
          editCell={jest.fn()}
          onGridSort={jest.fn()}
          selectedRowIndexes={[]}
          setDropdownAction={jest.fn()}
          onSetSelectedRowIndexes={jest.fn()}
          reorderColumn={jest.fn()}
          {...extraProps /* may include new loadRows */}
        />
      </Provider>
    )

    await tick() // wait for updateSize(), which actually renders the grid
    ret.update()

    return ret
  }

  it('Renders the grid', async () => {
    const loadRows = jest.fn()
    let resolveHttpRequest
    loadRows.mockReturnValueOnce(new Promise(resolve => { resolveHttpRequest = resolve }))

    const tree = await wrapper({ loadRows, nRows: 2 })

    // Check that we ended up with five columns (first is row number), with the right names
    // If rows values are not present, ensure intial DataGrid state.gridHeight > 0
    expect(tree.find('HeaderCell')).toHaveLength(5)

    // We now test the headers separately
    expect(tree.find('EditableColumnName')).toHaveLength(4)
    expect(tree.find('EditableColumnName').get(0).props.columnKey).toBe('aaa')
    expect(tree.find('EditableColumnName').get(1).props.columnKey).toBe('bbbb')
    expect(tree.find('EditableColumnName').get(2).props.columnKey).toBe('getCell')
    expect(tree.find('EditableColumnName').get(3).props.columnKey).toBe('select-row')

    // no spinner at first
    expect(tree.find('.spinner-container-transparent')).toHaveLength(0)
    // No content except row numbers
    expect(tree.find('.react-grid-Viewport').text()).toMatch(/12/)

    expect(loadRows).toHaveBeenCalledWith(1, 2, 0, 200)

    resolveHttpRequest(testRows); await tick(); tree.update()

    // Match all cell values -- including row numbers 1 and 2.
    expect(tree.find('.react-grid-Viewport').text()).toMatch(/.*9.*foo.*9.*someval.*1.*9.*baz.*someotherval.*2/)
  })

  it('should edit a cell', async () => {
    const tree = await wrapper()
    await tick(); tree.update() // load data
    // weird incantation to simulate double-click
    tree.find('.react-grid-Cell').first().simulate('click')
    tree.find('.react-grid-Cell').first().simulate('doubleClick')
    const input = tree.find('EditorContainer')
    input.find('input').instance().value = 'X' // react-data-grid has a weird way of editing cells
    input.simulate('keyDown', { key: 'Enter' })
    expect(tree.find('DataGrid').prop('editCell')).toHaveBeenCalledWith(0, 'aaa', 'X')
  })

  it('should not edit a cell when its value does not change', async () => {
    const tree = await wrapper()
    await tick(); tree.update() // load data
    // weird incantation to simulate double-click
    tree.find('.react-grid-Cell').first().simulate('click')
    tree.find('.react-grid-Cell').first().simulate('doubleClick')
    const input = tree.find('EditorContainer')
    input.simulate('keyDown', { key: 'Enter' })
    expect(tree.find('DataGrid').prop('editCell')).not.toHaveBeenCalled()
  })

  it('should render as a placeholder that loads no data', async () => {
    const tree = await wrapper({}, [])

    expect(tree.find('.spinner-container-transparent')).toHaveLength(0)
    expect(tree.text()).not.toMatch(/null/) // show blank cells, not "null" placeholders

    await tick(); tree.update() // ensure nothing happens
    expect(tree.find('DataGrid').prop('loadRows')).not.toHaveBeenCalled()
  })

  it('should show letters in the header', async () => {
    const tree = await wrapper({})
    expect(tree.find('.column-letter')).toHaveLength(4)
    expect(tree.find('.column-letter').at(0).text()).toEqual('A')
    expect(tree.find('.column-letter').at(1).text()).toEqual('B')
    expect(tree.find('.column-letter').at(2).text()).toEqual('C')
    expect(tree.find('.column-letter').at(3).text()).toEqual('D')
  })

  it('should respect isReadOnly for rename columns', async () => {
    const tree = await wrapper({ isReadOnly: true })
    tree.find('EditableColumnName').first().simulate('click')
    tree.update()
    expect(tree.find('EditableColumnName input')).toHaveLength(0)
  })

  it('should set className to include type', async () => {
    const tree = await wrapper()
    await tick(); tree.update() // load data
    expect(tree.find('.cell-text')).toHaveLength(6)
    expect(tree.find('.cell-number')).toHaveLength(2)
  })

  it('should display "null" for none types', async () => {
    const tree = await wrapper({}, [{
      start_row: 0,
      end_row: 1,
      rows: [
        {
          aaa: null,
          bbbb: null,
          getCell: null,
          'select-row': null
        }
      ]
    }])
    await tick(); tree.update() // load data
    expect(tree.find('.cell-null')).toHaveLength(4)
  })

  it('should select a row', async () => {
    const tree = await wrapper()
    await tick(); tree.update() // load data
    expect(tree.find('input[type="checkbox"]').at(1).prop('checked')).toBe(false)
    tree.find('input[type="checkbox"]').at(1).simulate('change', { target: { checked: true } })
    expect(tree.find('DataGrid').prop('onSetSelectedRowIndexes')).toHaveBeenCalledWith([1])
  })

  it('should deselect a row', async () => {
    const tree = await wrapper({ selectedRowIndexes: [1] })
    await tick(); tree.update() // load data
    expect(tree.find('input[type="checkbox"]').at(1).prop('checked')).toBe(true)
    tree.find('input[type="checkbox"]').at(1).simulate('change', { target: { checked: false } })
    expect(tree.find('DataGrid').prop('onSetSelectedRowIndexes')).toHaveBeenCalledWith([])
  })

  it('should lazily load rows as needed', async () => {
    function result (start = 0) {
      const arr = []
      for (let i = 0; i < 200; i++) {
        arr[i] = {
          aaa: null,
          bbbb: String(start + i),
          getCell: null,
          'select-row': null
        }
      }
      return {
        start_row: start,
        end_row: start + 200,
        rows: arr
      }
    }

    const tree = await wrapper({ nRows: 801 }, [result(0), result(200), result(600)])
    const loadRows = tree.find('DataGrid').prop('loadRows')

    // Should load 0..initialRows at first
    expect(loadRows).toHaveBeenCalledWith(1, 2, 0, 200)
    await tick(); tree.update() // let rows load

    // force load by reading a missing row
    const missingRowForNow = tree.find('DataGrid').instance().getRow(200)
    tree.find('DataGrid').instance().getRow(201) // spurious getRow() -- there are lots
    expect(missingRowForNow).not.toBe(null)
    await tick() // begin load
    expect(loadRows).toHaveBeenCalledWith(1, 2, 200, 400)
    expect(loadRows).not.toHaveBeenCalledWith(1, 2, 201, 401)
    await tick(); tree.update() // let load finish

    // read a row, _not_ forcing a load
    const nonMissingRow = tree.find('DataGrid').instance().getRow(201)
    expect(nonMissingRow.bbbb).toEqual('201')
    expect(loadRows).not.toHaveBeenCalledWith(1, 2, 201, 401)

    // force another load (to test we keep loading)
    tree.find('DataGrid').instance().getRow(600)
    await tick() // begin load
    expect(loadRows).toHaveBeenCalledWith(1, 2, 600, 800)
    await tick(); tree.update() // let load finish
  })
})
