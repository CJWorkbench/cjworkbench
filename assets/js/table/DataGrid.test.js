/* globals beforeEach, describe, expect, it, jest */
import '../__mocks__/ResizeObserver'
import { act } from 'react-dom/test-utils'
import { Provider } from 'react-redux'
import { mountWithI18n } from '../i18n/test-utils'
import { mockStore, tick } from '../test-utils'
import DataGrid from './DataGrid'

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

describe('DataGrid', () => {
  // Column names are chosen to trigger
  // https://github.com/adazzle/react-data-grid/issues/1269 and
  // https://github.com/adazzle/react-data-grid/issues/1270
  const testColumns = [
    { name: 'aaa', type: 'number', format: '{:,}' },
    { name: 'bbbb', type: 'text' },
    // try and trigger https://github.com/adazzle/react-data-grid/issues/1270
    { name: 'getCell', type: 'text' },
    // try and trigger https://github.com/adazzle/react-data-grid/issues/1269
    { name: 'select-row', type: 'text' }
  ]

  const testRows = [
    [9, 'foo', '9', 'someval'],
    [9, '', 'baz', 'someotherval']
  ]

  // mount() so we get componentDidMount, componentWillUnmount()
  const wrapper = async (extraProps = {}, httpResponses = [testRows]) => {
    for (const httpResponse of httpResponses) {
      global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, { rows: httpResponse })))
    }

    // mock store for <ColumnHeader>, a descendent
    const store = mockStore({ modules: {} })

    const nRows = httpResponses.reduce((s, j) => s + j.length, 0)

    return mountWithI18n(
      <Provider store={store}>
        <DataGrid
          workflowIdOrSecretId={1}
          isReadOnly={false}
          stepId={1}
          stepSlug='step-1'
          deltaId={2}
          columns={testColumns}
          nRows={nRows}
          nRowsPerTile={100}
          nColumnsPerTile={50}
          editCell={jest.fn()}
          onGridSort={jest.fn()}
          selectedRowIndexes={[]}
          setDropdownAction={jest.fn()}
          onSetSelectedRowIndexes={jest.fn()}
          reorderColumn={jest.fn()}
          {
            ...extraProps /* may include new loadRows */
          }
        />
      </Provider>
    )
  }

  it('Renders the grid', async () => {
    let resolveHttpRequest
    global.fetch.mockReturnValueOnce(new Promise((resolve, reject) => {
      resolveHttpRequest = resolve
    }))

    const tree = await wrapper({ nRows: 2 })

    // Check that we ended up with five columns (first is row number), with the right names
    // If rows values are not present, ensure intial DataGrid state.gridHeight > 0
    expect(tree.find('thead th')).toHaveLength(5)

    // We now test the headers separately
    expect(tree.find('EditableColumnName')).toHaveLength(4)
    expect(tree.find('EditableColumnName').get(0).props.columnKey).toBe('aaa')
    expect(tree.find('EditableColumnName').get(1).props.columnKey).toBe('bbbb')
    expect(tree.find('EditableColumnName').get(2).props.columnKey).toBe('getCell')
    expect(tree.find('EditableColumnName').get(3).props.columnKey).toBe('select-row')

    expect(tree.find('tbody').text()).toEqual('12') // just row numbers

    expect(global.fetch).toHaveBeenCalledWith('/workflows/1/tiles/step-1/delta-2/0,0.json', expect.anything())
    await act(async () => {
      resolveHttpRequest(new MockHttpResponse(200, { rows: testRows }))
    })

    // Match all cell values -- including row numbers 1 and 2.
    expect(tree.find('tbody').text()).toEqual('19foo9someval29bazsomeotherval')
  })

  it('should render a zero-row table', async () => {
    const tree = await wrapper({ nRows: 0 })
    expect(tree.find('tbody tr')).toHaveLength(0)
    expect(global.fetch).not.toHaveBeenCalled()
  })

  it('should show letters in the header', async () => {
    const tree = await wrapper({ nRows: 0 })
    expect(tree.find('.column-letter')).toHaveLength(4)
    expect(tree.find('.column-letter').at(0).text()).toEqual('A')
    expect(tree.find('.column-letter').at(1).text()).toEqual('B')
    expect(tree.find('.column-letter').at(2).text()).toEqual('C')
    expect(tree.find('.column-letter').at(3).text()).toEqual('D')
  })

  it('should allow editing columns', async () => {
    const tree = await wrapper({ isReadOnly: false, nRows: 0 })
    tree.find('EditableColumnName').first().simulate('click')
    expect(tree.find('EditableColumnName input')).toHaveLength(1)
  })

  it('should respect isReadOnly for rename columns', async () => {
    const tree = await wrapper({ isReadOnly: true, nRows: 0 })
    tree.find('EditableColumnName').first().simulate('click')
    expect(tree.find('EditableColumnName input')).toHaveLength(0)
  })

  it('should set className to include type', async () => {
    const tree = await wrapper({ nRows: 2 })
    await act(async () => await tick()) // load data
    expect(tree.find('.cell-text')).toHaveLength(6)
    expect(tree.find('.cell-number')).toHaveLength(2)
  })

  it('should display "null" for none types', async () => {
    const tree = await wrapper({ nRows: 1 }, [[null, null, null, null]])
    await act(async () => await tick()) // load data
    expect(tree.find('.cell-null')).toHaveLength(4)
  })
})
