/* global beforeEach, describe, it, expect, jest, test */
import '../__mocks__/ResizeObserver'
import { act } from 'react-dom/test-utils'
import { createEvent, fireEvent } from '@testing-library/react'
import { renderWithI18n } from '../i18n/test-utils'
import { Provider } from 'react-redux'
import { mockStore, tick } from '../test-utils'
import { generateSlug } from '../utils'
import ConnectedTableView from './TableView'

jest.mock('../utils')

global.fetch = jest.fn(() => Promise.reject(new Error('Mock me')))
beforeEach(() => global.fetch.mockClear())

/*
 * Help BigTable/Viewport.js calculate the wanted parts of the table.
 *
 * These are globals! They apply to all tests in this file.
 *
 * <th> -- has x=0, width=60, height=30; also, has a non-null .offsetParent
 * <div> (viewport) -- has width=650, height=200
 *
 * Each non-header cell has width=180. That's a magic number somewhere....
 */
global.HTMLTableCellElement.prototype.getBoundingClientRect = () => (
  { x: 0, width: 60, height: 30 }
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

function renderWithDefaults ({ store, ...props }) {
  // mock store for <SelectedRowsActions>, a descendent
  if (!store) {
    store = mockStore({
      settings: {
        bigTableColumnsPerTile: 4,
        bigTableRowsPerTile: 5
      }
    })
  }

  return renderWithI18n(
    <Provider store={store}>
      <ConnectedTableView
        isReadOnly={false}
        workflowIdOrSecretId='w123'
        stepSlug='step-1'
        stepId={100}
        deltaId={2}
        status='ok'
        columns={[
          { name: 'ColA', type: 'text' },
          { name: 'ColB', type: 'text' },
          { name: 'ColC', type: 'text' }
        ]}
        nRows={0}
        {...props}
      />
    </Provider>
  )
}

test('reorder columns', async () => {
  // integration-test style -- these moving parts tend to rely on one another
  // lots: ignoring workflow-reducer means tests miss bugs.
  const api = { addStep: jest.fn(() => Promise.resolve(null)) }
  generateSlug.mockImplementationOnce(prefix => prefix + 'X')
  const store = mockStore(
    {
      settings: {
        bigTableColumnsPerTile: 4,
        bigTableRowsPerTile: 5
      },
      workflow: {
        tab_slugs: ['tab-1']
      },
      tabs: {
        'tab-1': { step_ids: [2, 3], selected_step_position: 0 }
      },
      steps: {
        2: { slug: 'step-2', tab_slug: 'tab-1' },
        3: {}
      },
      modules: {
        reordercolumns: {}
      }
    },
    api
  )
  global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
    rows: [
      ['a1', 'b1', 'c1'],
      ['a2', 'b2', 'c2']
    ]
  })))
  const { getByText, debug } = renderWithDefaults({ store, stepId: 2, nRows: 2 })
  await act(async () => await tick()) // load data

  const dragStartEvent = createEvent.dragStart(getByText('C'))
  Object.defineProperty(
    dragStartEvent,
    'dataTransfer',
    {
      value: {
        effectAllowed: [],
        dropEffect: 'copy',
        setData: jest.fn()
      }
    }
  )
  fireEvent(getByText('C'), dragStartEvent) // start dragging letter
  expect(dragStartEvent.dataTransfer.effectAllowed).toEqual(['move'])
  expect(dragStartEvent.dataTransfer.dropEffect).toBe('move')
  expect(dragStartEvent.dataTransfer.setData).toHaveBeenCalledWith('text/plain', 'ColC')

  fireEvent.drop(getByText('A').closest('th').querySelector('.column-reorder-drop-zone.align-right'))
  fireEvent.dragEnd(getByText('C'))
  expect(api.addStep).toHaveBeenCalledWith(
    'tab-1',
    'step-X',
    'reordercolumns',
    1,
    {
      'reorder-history': '[{"column":"ColC","to":1,"from":2}]'
    }
  )
})

test('edit a cell', async () => {
  // integration-test style -- these moving parts tend to rely on one another
  // lots: ignoring workflow-reducer means tests miss bugs.
  const api = {
    addStep: jest.fn().mockImplementation(() => Promise.resolve(null))
  }
  generateSlug.mockImplementationOnce(prefix => prefix + 'X')
  const store = mockStore(
    {
      settings: {
        bigTableColumnsPerTile: 4,
        bigTableRowsPerTile: 5
      },
      workflow: {
        tab_slugs: ['tab-1']
      },
      tabs: {
        'tab-1': { step_ids: [100, 3], selected_step_position: 0 }
      },
      steps: {
        100: { slug: 'step-2', tab_slug: 'tab-1' },
        3: {}
      },
      modules: {
        editcells: {}
      }
    },
    api
  )
  global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
    rows: [
      ['a1', 'b1', 'c1'],
      ['a2', 'b2', 'c2']
    ]
  })))
  const { getByDisplayValue, getByText } = renderWithDefaults({ store, nRows: 2 })
  await act(async () => await tick()) // load data
  fireEvent.mouseDown(getByText('c1'))
  fireEvent.doubleClick(getByText('c1'))
  fireEvent.change(getByDisplayValue('c1'), { target: { value: 'c1 - edited' } })
  fireEvent.blur(getByDisplayValue('c1 - edited'))
  expect(api.addStep).toHaveBeenCalledWith(
    'tab-1',
    'step-X',
    'editcells',
    1,
    {
      celledits: [{ row: 0, col: 'ColC', value: 'c1 - edited' }]
    }
  )
  getByText('c1 - edited') // don't revert to "c1" after we stop editing
})

test('not edit a cell when its value does not change', async () => {
  // integration-test style -- these moving parts tend to rely on one another
  // lots: ignoring workflow-reducer means tests miss bugs.
  const api = {
    addStep: jest.fn().mockImplementation(() => Promise.resolve(null))
  }
  generateSlug.mockImplementationOnce(prefix => prefix + 'X')
  const store = mockStore(
    {
      settings: {
        bigTableColumnsPerTile: 4,
        bigTableRowsPerTile: 5
      },
      workflow: {
        tab_slugs: ['tab-1']
      },
      tabs: {
        'tab-1': { step_ids: [100, 3], selected_step_position: 0 }
      },
      steps: {
        100: { slug: 'step-2', tab_slug: 'tab-1' },
        3: {}
      },
      modules: {
        editcells: {}
      }
    },
    api
  )
  global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
    rows: [
      ['a1', 'b1', 'c1'],
      ['a2', 'b2', 'c2']
    ]
  })))
  const { getByDisplayValue, getByText } = renderWithDefaults({ store, nRows: 2 })
  await act(async () => await tick()) // load data
  fireEvent.mouseDown(getByText('c1'))
  fireEvent.doubleClick(getByText('c1'))
  fireEvent.change(getByDisplayValue('c1'), { target: { value: 'c1 - edited' } })
  fireEvent.change(getByDisplayValue('c1 - edited'), { target: { value: 'c1' } })
  fireEvent.blur(getByDisplayValue('c1'))
  expect(api.addStep).not.toHaveBeenCalled()
})

it('should not edit a Number cell when its value does not change', async () => {
  // integration-test style -- these moving parts tend to rely on one another
  // lots: ignoring workflow-reducer means tests miss bugs.
  const api = {
    addStep: jest.fn().mockImplementation(() => Promise.resolve(null))
  }
  generateSlug.mockImplementationOnce(prefix => prefix + 'X')
  const store = mockStore(
    {
      settings: {
        bigTableColumnsPerTile: 4,
        bigTableRowsPerTile: 5
      },
      workflow: {
        tab_slugs: ['tab-1']
      },
      tabs: {
        'tab-1': { step_ids: [100, 3], selected_step_position: 0 }
      },
      steps: {
        100: { slug: 'step-2', tab_slug: 'tab-1' },
        3: {}
      },
      modules: {
        editcells: {}
      }
    },
    api
  )
  global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, { rows: [[99]] })))
  const { getByDisplayValue, getByText } = renderWithDefaults({
    store,
    columns: [{ name: 'A', type: 'number'}],
    nRows: 1
  })
  await act(async () => await tick()) // load data
  fireEvent.mouseDown(getByText('99'))
  fireEvent.doubleClick(getByText('99'))
  fireEvent.change(getByDisplayValue('99'), { target: { value: '100' } })
  fireEvent.change(getByDisplayValue('100'), { target: { value: '99' } })
  // Number blur has different logic from text blur. 2021-05-25 this led to
  // a crash when comparing.
  fireEvent.blur(getByDisplayValue('99'))
  expect(api.addStep).not.toHaveBeenCalled()
})

test('resize a column', async () => {
  global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
    rows: [
      ['a1', 'b1', 'c1'],
      ['a2', 'b2', 'c2']
    ]
  })))
  const { container, getByText } = renderWithDefaults({ nRows: 2 })
  await act(async () => await tick()) // load data
  const handle = getByText('A').closest('th').querySelector('.resize-handle')
  fireEvent.mouseDown(handle, { button: 0, target: handle })
  await act(async () => await tick()) // load data
  fireEvent.mouseMove(document, { clientX: 100 })
  await act(async () => await tick()) // load data
  expect(container.querySelectorAll('col')[1].getAttribute('style')).toEqual('width: 100px;')
})


test('select a row', async () => {
  global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
    rows: [
      ['a1', 'b1', 'c1'],
      ['a2', 'b2', 'c2']
    ]
  })))
  const { getByLabelText } = renderWithDefaults({ nRows: 2 })
  await act(async () => await tick()) // load data
  expect(getByLabelText('2').checked).toBe(false)
  fireEvent.click(getByLabelText('2'))
  expect(getByLabelText('2').checked).toBe(true)
})

test('focus a row (not cell) when clicking the <th>', async () => {
  global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
    rows: [
      ['a1', 'b1', 'c1'],
      ['a2', 'b2', 'c2']
    ]
  })))
  const { getByLabelText } = await renderWithDefaults({ nRows: 2 })
  await act(async () => await tick()) // load data
  fireEvent.click(getByLabelText('2'))
  expect(getByLabelText('2').closest('th').getAttribute('class')).toBe('focus')
})

test('clear selection when clicking a <td>', async () => {
  global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
    rows: [
      ['a1', 'b1', 'c1'],
      ['a2', 'b2', 'c2']
    ]
  })))
  const { getByLabelText, getByText } = await renderWithDefaults({ nRows: 2 })
  await act(async () => await tick()) // load data
  fireEvent.click(getByLabelText('2')) // select row
  fireEvent.mouseDown(getByText('c2')) // focus cell
  expect(getByLabelText('2').closest('th').getAttribute('class')).toBe(null)
})

test('focus a cell after tabbing in, using only the keyboard', async () => {
  // When we design a nice keyboard-usability feature, rewrite this sequence.
  // For now, we're merely testing that it is *possible* to focus with keyboard.
  global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
    rows: [
      ['a1', 'b1', 'c1'],
      ['a2', 'b2', 'c2']
    ]
  })))
  const { getByText } = await renderWithDefaults({ nRows: 2 })
  await act(async () => await tick()) // load data
  const tbody = getByText('c2').closest('tbody')
  fireEvent.keyDown(tbody, { key: 'ArrowDown' })
  fireEvent.keyDown(tbody, { key: 'ArrowRight' })
  expect(getByText('a1').closest('td').getAttribute('class')).toBe('type-text focus')
})

test('focus a row after tabbing in, using only the keyboard', async () => {
  // When we design a nice keyboard-usability feature, rewrite this sequence.
  // For now, we're merely testing that it is *possible* to focus with keyboard.
  global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
    rows: [
      ['a1', 'b1', 'c1'],
      ['a2', 'b2', 'c2']
    ]
  })))
  const { getByLabelText, getByText } = await renderWithDefaults({ nRows: 2 })
  await act(async () => await tick()) // load data
  const tbody = getByText('c2').closest('tbody')
  fireEvent.keyDown(tbody, { key: 'ArrowDown' })
  expect(getByLabelText('1').closest('th').getAttribute('class')).toBe('focus')
})

test('focus a cell on mousedown', async () => {
  global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
    rows: [
      ['a1', 'b1', 'c1'],
      ['a2', 'b2', 'c2']
    ]
  })))
  const { getByText } = await renderWithDefaults({ nRows: 2 })
  await act(async () => await tick()) // load data
  fireEvent.mouseDown(getByText('a2'), { button: 0 })
  expect(getByText('a2').closest('td').getAttribute('class')).toBe('type-text focus')
})

test('focus 20 rows up/down on PageUp/PageDown', async () => {
  global.fetch.mockReturnValueOnce(Promise.resolve(new MockHttpResponse(200, {
    rows: [
      ['a1', 'b1', 'c1'],
      ['a2', 'b2', 'c2'],
      ['a3', 'b3', 'c3'],
      ['a4', 'b4', 'c4'],
      ['a5', 'b5', 'c5'],
      ['a6', 'b6', 'c6'],
      ['a7', 'b7', 'c7'],
      ['a8', 'b8', 'c8'],
      ['a9', 'b9', 'c9'],
      ['a10', 'b10', 'c10'],
      ['a11', 'b11', 'c11'],
      ['a12', 'b12', 'c12'],
      ['a13', 'b13', 'c13'],
      ['a14', 'b14', 'c14'],
      ['a15', 'b15', 'c15'],
      ['a16', 'b16', 'c16'],
      ['a17', 'b17', 'c17'],
      ['a18', 'b18', 'c18'],
      ['a19', 'b19', 'c19'],
      ['a20', 'b20', 'c20'],
      ['a21', 'b21', 'c21'],
      ['a22', 'b22', 'c22'],
      ['a23', 'b23', 'c23'],
      ['a24', 'b24', 'c24'],
      ['a25', 'b25', 'c25'],
      ['a26', 'b26', 'c26'],
      ['a27', 'b27', 'c27'],
    ]
  })))
  const { getByText } = await renderWithDefaults({
    store: mockStore({ settings: { bigTableRowsPerTile: 50, bigTableColumnsPerTile: 5 } }),
    nRows: 27
  })
  await act(async () => await tick()) // load data
  const tbody = getByText('a2').closest('tbody')
  fireEvent.mouseDown(getByText('a2'), { button: 0 })
  fireEvent.keyDown(tbody, { key: 'PageDown' })
  expect(getByText('a22').closest('td').getAttribute('class')).toBe('type-text focus')
  fireEvent.keyDown(tbody, { key: 'ArrowDown' })
  fireEvent.keyDown(tbody, { key: 'PageUp' })
  expect(getByText('a3').closest('td').getAttribute('class')).toBe('type-text focus')
})
