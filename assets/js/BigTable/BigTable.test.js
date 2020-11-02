/* globals expect, test */
import React from 'react'
import { prettyDOM } from '@testing-library/react'
import { render } from '@testing-library/react'

import BigTable from './BigTable'

test("Empty table", () => {
  const column = {
    width: 60,
    headerComponent: () => <>HEADER</>,
    valueComponent: ({ value }) => <>value: {value}</>
  }

  const { container } = render(
    <BigTable
      sparseTileGrid={[]}
      nRows={0}
      columns={[column]}
      nRowsPerTile={100}
      nColumnsPerTile={10}
      setWantedTileRange={() => {}}
    />
  )
  expect(container.querySelectorAll('th')).toHaveLength(2) // 1 column, row-number column
  expect(container.querySelector('tbody')).toBe(null)
})

test("Table with a gap", () => {
  const A = {
    width: 60,
    headerComponent: () => <>HEADER A</>,
    valueComponent: ({ value }) => <>A: {value}</>
  }
  const B = {
    width: 61,
    headerComponent: () => <>HEADER B</>,
    valueComponent: ({ value }) => <>B: {value}</>
  }

  const { container, queryByText } = render(
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
      setWantedTileRange={() => {}}
    />
  )
  expect(container.querySelectorAll('thead th')).toHaveLength(3) // 2 column, row-number column
  expect(container.querySelector('tbody.gap td[colspan="3"][rowspan="6"]')).toBeInTheDocument()
  expect(container.querySelectorAll('tbody')).toHaveLength(3)
  expect(queryByText('A: A1')).toBeInTheDocument()
  expect(queryByText('B: B1')).toBeInTheDocument()
  expect(queryByText('A: A11')).toBeInTheDocument()
  expect(queryByText('B: B11')).toBeInTheDocument()
  expect(container.querySelector('tbody+tbody').childNodes).toHaveLength(1) // a gap is one big row
  expect(container).toMatchSnapshot()
})
