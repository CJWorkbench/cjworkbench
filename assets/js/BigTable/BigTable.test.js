/* globals expect, test */
import React from 'react'

import '../__mocks__/ResizeObserver'
import { renderWithI18n } from '../i18n/test-utils'
import BigTable from './BigTable'

test('Empty table', async () => {
  const column = {
    width: 60,
    type: 'text',
    headerComponent: () => <>HEADER</>,
    valueComponent: ({ value }) => <>value: {value}</>
  }

  const { container } = renderWithI18n(
    <BigTable
      sparseTileGrid={[]}
      nRows={0}
      columns={[column]}
      nRowsPerTile={100}
      nColumnsPerTile={10}
      fixedCellRange={[0, 0, 0, 1]}
      setWantedTileRange={() => {}}
    />
  )
  expect(container.querySelectorAll('th')).toHaveLength(2) // 1 column, row-number column
  expect(container.querySelector('tbody tr')).toBe(null)
})

test('Table with a gap', async () => {
  const A = {
    width: 60,
    type: 'number',
    headerComponent: () => <>HEADER A</>,
    valueComponent: ({ value }) => <>A: {value || 'NULL'}</>
  }
  const B = {
    width: 61,
    type: 'text',
    headerComponent: () => <>HEADER B</>,
    valueComponent: ({ value }) => <>B: {value || 'NULL'}</>
  }

  const { container, queryByText, getAllByText } = renderWithI18n(
    <BigTable
      sparseTileGrid={[
        [
          [['A1'], ['A2'], ['A3']],
          [['B1'], ['B2'], ['B3']]
        ],
        2,
        [
          [['A10'], ['A11']],
          [['B10'], ['B11']]
        ]
      ]}
      nRows={11}
      columns={[A, B]}
      nRowsPerTile={3}
      nColumnsPerTile={1}
      fixedCellRange={[0, 11, 0, 2]}
      setWantedTileRange={() => {}}
    />
  )
  expect(container.querySelectorAll('thead th')).toHaveLength(3) // 2 column, row-number column
  expect(queryByText('A: A1')).toBeInTheDocument()
  expect(queryByText('B: B1')).toBeInTheDocument()
  expect(queryByText('A: A11')).toBeInTheDocument()
  expect(queryByText('B: B11')).toBeInTheDocument()
  expect(getAllByText('A: NULL')).toHaveLength(6)
  expect(getAllByText('B: NULL')).toHaveLength(6)
  expect(container).toMatchSnapshot()
})
