/* globals expect, test */
import React from 'react'
import { render } from '@testing-library/react'

import TileRow from './TileRow'

test('render loaded tiles', () => {
  function A({ value }) { return <>A: {JSON.stringify(value)}</> }
  function B({ value }) { return <>B: {JSON.stringify(value)}</> }
  function C({ value }) { return <>C: {JSON.stringify(value)}</> }
  function D({ value }) { return <>D: {JSON.stringify(value)}</> }
  function E({ value }) { return <>E: {JSON.stringify(value)}</> }
  function RowNumber({ index }) { return <>ROW: {index}</> }

  const { getByText } = render(
    <table>
      <TileRow
        tiles={[
          [
            ['A1', 'B1', 'C1'],
            ['A2', 'B2', 'C2'],
            ['A3', 'B3', 'C3']
          ], [
            ['D1', 'E1'],
            ['D2', 'E2'],
            ['D3', 'E3']
          ]
        ]}
        nRows={3}
        rowIndex={100}
        tiledColumnComponents={[[A, B, C], [D, E]]}
        rowNumberComponent={RowNumber}
      />
    </table>
  )
  expect(getByText('A: "A1"')).toBeInTheDocument()
  expect(getByText('E: "E3"')).toBeInTheDocument()
  expect(getByText('ROW: 100')).toBeInTheDocument()
  expect(getByText('ROW: 102')).toBeInTheDocument()
})

test('render loading tiles', () => {
  function Tile(props) { return <>TILE</> }
  function RowNumber({ index }) { return <>ROW: {index}</> }

  const { getByText } = render(
    <table>
      <TileRow
        tiles={[null, null]}
        nRows={4}
        rowIndex={100}
        tiledColumnComponents={[[Tile, Tile, Tile], [Tile, Tile]]}
        rowNumberComponent={RowNumber}
      />
    </table>
  )
  expect(getByText('ROW: 103')).toBeInTheDocument()
  expect(() => getByText('TILE')).toThrow()
})

test('render error tiles', () => {
  function Tile(props) { return <>TILE</> }
  function RowNumber({ index }) { return <>ROW: {index}</> }

  const { getByText } = render(
    <table>
      <TileRow
        tiles={[{error: { name: 'ENAME', message: 'EMESSAGE' } }, null]}
        nRows={4}
        rowIndex={100}
        tiledColumnComponents={[[Tile, Tile, Tile], [Tile, Tile]]}
        rowNumberComponent={RowNumber}
      />
    </table>
  )
  expect(getByText('ROW: 103')).toBeInTheDocument()
  expect(getByText('ENAME: EMESSAGE')).toBeInTheDocument()
})
