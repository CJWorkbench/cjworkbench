/* globals expect, jest, test */
import { useEffect } from 'react'
import { act, render, waitFor } from '@testing-library/react'
import { AbortError } from 'node-fetch'

import useTiles from './useTiles'

class MockFetchResult {
  constructor ({
    status = 200,
    statusText = 'OK',
    json = null,
    body = null,
    requestOptions = {}
  }) {
    this.status = status
    this.statusText = statusText
    this.requestOptions = requestOptions
    this._body = body
    this._json = json
  }

  async json () {
    if (this.requestOptions.signal && this.requestOptions.signal.aborted) {
      throw new AbortError()
    }
    if (this._json === null) {
      throw new Error('Oops -- pass json to constructor')
    }

    return this._json
  }
}

test('memoize the empty result', () => {
  let nChanges = 0
  let lastRenderNumber = 0
  const fetchTile = jest.fn()
  function NoisyComponent ({ renderNumber }) {
    const { sparseTileGrid, setWantedTileRange, isLoading } = useTiles({
      fetchTile, // unused
      nTileRows: 0,
      nTileColumns: 2
    })
    useEffect(() => {
      nChanges++
    }, [sparseTileGrid, setWantedTileRange, isLoading])
    useEffect(() => {
      lastRenderNumber = renderNumber
    }, [renderNumber])
    return <div />
  }

  const { rerender } = render(<NoisyComponent renderNumber={1} />)
  expect(lastRenderNumber).toEqual(1)
  expect(nChanges).toEqual(1)
  act(() => rerender(<NoisyComponent renderNumber={2} />))
  expect(lastRenderNumber).toEqual(2)
  expect(nChanges).toEqual(1)
})

test('memoize a loading tile', async () => {
  let nChanges = 0
  let lastRenderNumber = 0
  const fetchTileResult = Promise.resolve(
    new MockFetchResult({ json: { tileRow: 0, tileColumn: 0, rows: [['X']] } })
  )
  const fetchTile = () => fetchTileResult
  function NoisyComponent ({ renderNumber }) {
    const { sparseTileGrid, setWantedTileRange, isLoading } = useTiles({
      fetchTile,
      nTileRows: 1,
      nTileColumns: 1
    })
    useEffect(() => {
      nChanges++
    }, [sparseTileGrid, setWantedTileRange, isLoading])
    useEffect(() => {
      lastRenderNumber = renderNumber
    }, [renderNumber])
    return <div />
  }

  const { rerender } = render(<NoisyComponent renderNumber={1} />)
  expect(lastRenderNumber).toEqual(1)
  expect(nChanges).toEqual(1) // sparseTileGrid = [[LoadingTile]]
  rerender(<NoisyComponent renderNumber={2} />)
  expect(lastRenderNumber).toEqual(2)
  expect(nChanges).toEqual(1) // sparseTileGrid = [[LoadingTile]] _and the value did not change_
  await act(() => fetchTileResult) // wait for effects to finish
  expect(nChanges).toEqual(2) // sparseTileGrid = [[Tile:[['X']]]]
})

test('load when started', async () => {
  const fetchTileResult = Promise.resolve(
    new MockFetchResult({
      json: { tileRow: 0, tileColumn: 0, rows: [['foo', 'bar']] }
    })
  )
  function fetchTile () {
    return fetchTileResult
  }

  function Table (props) {
    const { isLoading } = useTiles({
      fetchTile,
      nTileRows: 1,
      nTileColumns: 1
    })
    return <div>{isLoading ? 'loading' : 'loaded'}</div>
  }
  const { getByText } = render(<Table fetchTile={fetchTile} />)
  expect(getByText('loading')).toBeInTheDocument()
  await waitFor(() => expect(getByText('loaded')).toBeInTheDocument())
})

test('abort and start a new load when props change, with a non-memoized loading tile', async () => {
  const fetchTileXResult = Promise.resolve(
    new MockFetchResult({
      json: { tileRow: 0, tileColumn: 0, rows: [['foo', 'bar']] }
    })
  )
  const fetchTileYResult = Promise.resolve(
    new MockFetchResult({
      json: { tileRow: 0, tileColumn: 0, rows: [['bar', 'baz']] }
    })
  )
  const fetchTileX = jest.fn((tr, tc, requestOptions) => fetchTileXResult)
  const fetchTileY = jest.fn((tr, tc, requestOptions) => fetchTileYResult)

  function Table ({ fetchTile }) {
    const { sparseTileGrid, isLoading } = useTiles({
      fetchTile,
      nTileRows: 1,
      nTileColumns: 1
    })
    return <div>{isLoading ? 'loading' : sparseTileGrid[0][0][0][1]}</div>
  }
  const { rerender, getByText } = render(<Table fetchTile={fetchTileX} />)
  act(() => rerender(<Table fetchTile={fetchTileY} />))
  await waitFor(() => expect(getByText('baz')).toBeInTheDocument())
  expect(fetchTileX).toHaveBeenCalled()
  await waitFor(() => expect(fetchTileY).toHaveBeenCalled())
  expect(fetchTileX.mock.calls[0][2].signal.aborted).toBe(true)
})

test('handle error during HTTP request, making it a tile', async () => {
  const fetchTile = () => Promise.reject(new Error('oops'))

  function Table (props) {
    const { sparseTileGrid, isLoading } = useTiles({
      fetchTile,
      nTileRows: 1,
      nTileColumns: 1
    })
    return isLoading
      ? <div className='loading' />
      : (
        <div>
          <div className='errorType'>{sparseTileGrid[0][0].error.type}</div>
          <div className='errorName'>{sparseTileGrid[0][0].error.error.name}</div>
          <div className='errormessage'>
            {sparseTileGrid[0][0].error.error.message}
          </div>
        </div>
        )
  }
  const { getByText } = render(<Table />)
  await waitFor(() => expect(getByText('fetchError')).toBeInTheDocument())
  expect(getByText('Error')).toBeInTheDocument()
  expect(getByText('oops')).toBeInTheDocument()
})

test('handle error during fetch .json() call, making it a tile', async () => {
  let rej = null // call rej(new Error()) when wanted
  const httpJsonResult = new Promise((resolve, reject) => {
    rej = reject /* and never end */
  })
  const fetchTile = () =>
    Promise.resolve(new MockFetchResult({ json: httpJsonResult }))

  function Table (props) {
    const { sparseTileGrid, isLoading } = useTiles({
      fetchTile,
      nTileRows: 1,
      nTileColumns: 1
    })
    return isLoading
      ? <div className='loading' />
      : (
        <div>
          <div className='errorType'>{sparseTileGrid[0][0].error.type}</div>
          <div className='errorName'>{sparseTileGrid[0][0].error.error.name}</div>
          <div className='errormessage'>
            {sparseTileGrid[0][0].error.error.message}
          </div>
        </div>
        )
  }
  const { getByText } = render(<Table />)
  rej(new Error('oops'))
  await waitFor(() => expect(getByText('jsonError')).toBeInTheDocument())
  expect(getByText('Error')).toBeInTheDocument()
  expect(getByText('oops')).toBeInTheDocument()
})

test('request a new tile when wanted tiles change', async () => {
  const fetchTileXResult = Promise.resolve(
    new MockFetchResult({
      json: { tileRow: 0, tileColumn: 0, rows: [['foo']] }
    })
  )
  const fetchTileYResult = Promise.resolve(
    new MockFetchResult({
      json: { tileRow: 0, tileColumn: 1, rows: [['bar']] }
    })
  )

  const fetchTile = (_, tileColumn) =>
    tileColumn === 1 ? fetchTileYResult : fetchTileXResult

  const ensureTilesLoadedRef = { current: null }

  function Table (props) {
    const { sparseTileGrid, setWantedTileRange, isLoading } = useTiles({
      fetchTile,
      nTileRows: 1,
      nTileColumns: 2
    })
    useEffect(() => {
      ensureTilesLoadedRef.current = setWantedTileRange
    }, [setWantedTileRange])
    return isLoading
      ? <div className='loading' />
      : (
        <div>
          {sparseTileGrid.map((tileColumns, tileRow) => (
            <div key={tileRow}>
              {tileColumns.map((tile, tileColumn) => (
                <div key={tileColumn}>
                  r{tileRow}c{tileColumn} - {JSON.stringify(tile)}
                </div>
              ))}
            </div>
          ))}
        </div>
        )
  }
  const { getByText } = render(<Table fetchTile={fetchTile} />)
  await waitFor(() => expect(getByText('r0c0 - [["foo"]]')).toBeInTheDocument())
  act(() => ensureTilesLoadedRef.current(0, 1, 1, 2))
  await waitFor(() => expect(getByText('r0c1 - [["bar"]]')).toBeInTheDocument())
})

test('expand a gap and load it when wanted tiles change', async () => {
  const fetchTileXResult = Promise.resolve(
    new MockFetchResult({
      json: { tileRow: 0, tileColumn: 0, rows: [['foo']] }
    })
  )
  const fetchTileYResult = Promise.resolve(
    new MockFetchResult({
      json: { tileRow: 0, tileColumn: 1, rows: [['bar']] }
    })
  )

  const fetchTile = jest.fn(tileRow =>
    tileRow === 0 ? fetchTileXResult : fetchTileYResult
  )

  const ensureTilesLoadedRef = { current: null }

  function Table (props) {
    const { sparseTileGrid, setWantedTileRange } = useTiles({
      fetchTile,
      nTileRows: 5,
      nTileColumns: 1
    })
    useEffect(() => {
      ensureTilesLoadedRef.current = setWantedTileRange
    }, [setWantedTileRange])
    return (
      <div>
        {sparseTileGrid.map((tileColumns, tileRow) => (
          <div key={tileRow}>{JSON.stringify(tileColumns)}</div>
        ))}
      </div>
    )
  }
  const { getByText } = render(<Table fetchTile={fetchTile} />)
  await waitFor(() => expect(getByText('[[["foo"]]]')).toBeInTheDocument()) // row 0
  act(() => ensureTilesLoadedRef.current(3, 4, 0, 1))
  expect(getByText('2')).toBeInTheDocument() // rows 1-2
  expect(getByText('1')).toBeInTheDocument() // row 4
  expect(fetchTile).toHaveBeenCalledTimes(2)
  expect(fetchTile.mock.calls[1][0]).toEqual(3) // expanded row 3
  await waitFor(() => expect(getByText('[[["bar"]]]')).toBeInTheDocument())
})

test('continue requesting tiles (without abort) when requested rows are not all loaded', async () => {
  const fetchTile = (tileRow, tileColumn) =>
    Promise.resolve(
      new MockFetchResult({
        json: { tileRow, tileColumn, rows: [[`r${tileRow}c${tileColumn}`]] }
      })
    )

  function Table (props) {
    const { sparseTileGrid, setWantedTileRange } = useTiles({
      fetchTile,
      nTileRows: 2,
      nTileColumns: 3
    })
    useEffect(() => {
      setWantedTileRange(0, 2, 0, 3)
    }, [setWantedTileRange])
    return (
      <div>
        {sparseTileGrid.map((tileColumns, tileRow) => (
          <div key={tileRow}>{JSON.stringify(tileColumns)}</div>
        ))}
      </div>
    )
  }
  const { getByText } = render(<Table fetchTile={fetchTile} />)
  await waitFor(() =>
    expect(getByText('[[["r1c0"]],[["r1c1"]],[["r1c2"]]]')).toBeInTheDocument()
  ) // all done!
  expect(getByText('[[["r0c0"]],[["r0c1"]],[["r0c2"]]]')).toBeInTheDocument() // test that the rest are loaded, too
})

test('continue fetching other tiles on error', async () => {
  async function fetchTile (tileRow, tileColumn) {
    if (tileRow === 0) throw new Error('oops')
    return new MockFetchResult({
      json: { tileRow, tileColumn, rows: [[`r${tileRow}c${tileColumn}`]] }
    })
  }

  function Table (props) {
    const { sparseTileGrid, setWantedTileRange } = useTiles({
      fetchTile,
      nTileRows: 2,
      nTileColumns: 2
    })
    useEffect(() => {
      setWantedTileRange(0, 2, 0, 2)
    }, [setWantedTileRange])
    return (
      <div>
        {sparseTileGrid.map((tileColumns, tileRow) => (
          <div key={tileRow}>
            {Number.isInteger(tileColumns)
              ? String(tileColumns)
              : tileColumns.map((tile, tileColumn) => (
                <div key={tileColumn}>
                  r{tileRow}c{tileColumn}: {JSON.stringify(tile)}
                </div>
              ))}
          </div>
        ))}
      </div>
    )
  }
  const { getByText } = render(<Table fetchTile={fetchTile} />)
  await waitFor(() => expect(getByText('r1c1: [["r1c1"]]')).toBeInTheDocument()) // all done!
  // test that the rest are loaded, too
  expect(
    getByText(
      'r0c0: {"error":{"type":"fetchError","error":{"name":"Error","message":"oops"}}}'
    )
  ).toBeInTheDocument()
  expect(
    getByText(
      'r0c1: {"error":{"type":"fetchError","error":{"name":"Error","message":"oops"}}}'
    )
  ).toBeInTheDocument()
  expect(getByText('r1c0: [["r1c0"]]')).toBeInTheDocument()
})
