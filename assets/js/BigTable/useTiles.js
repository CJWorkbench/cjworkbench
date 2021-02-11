import { useReducer, useCallback, useEffect } from 'react'

import placeTile from './placeTile'
import findWantedLoadingTile from './findWantedLoadingTile'
import splitGapsIntoLoadingTiles from './splitGapsIntoLoadingTiles'

function createSparseTileGrid (nTileRows, nTileColumns) {
  const tileRows = []
  if (nTileRows > 0) {
    // first row: all loading
    tileRows.push(Array(nTileColumns).fill(null))

    if (nTileRows > 1) {
      // rest of rows: gap
      tileRows.push(nTileRows - 1)
    }
  }
  return tileRows
}

function init ({ nTileRows, nTileColumns }) {
  return {
    wantedTileRange: [0, 1, 0, 1],
    sparseTileGrid: createSparseTileGrid(nTileRows, nTileColumns),
    loadingTile: nTileRows === 0 ? null : { tileRow: 0, tileColumn: 0 }
  }
}

function handleFetchSuccess (state, { tileRow, tileColumn, rows }) {
  const sparseTileGrid = placeTile(
    state.sparseTileGrid,
    tileRow,
    tileColumn,
    rows
  )
  return {
    ...state,
    sparseTileGrid,
    loadingTile: findWantedLoadingTile(sparseTileGrid, ...state.wantedTileRange)
  }
}

function handleFetchError (state, { tileRow, tileColumn, error }) {
  const sparseTileGrid = placeTile(state.sparseTileGrid, tileRow, tileColumn, {
    error
  })
  return {
    ...state,
    sparseTileGrid,
    loadingTile: findWantedLoadingTile(sparseTileGrid, ...state.wantedTileRange)
  }
}

function handleSetWantedTileRange (state, r1, r2, c1, c2) {
  if (
    r1 === state.wantedTileRange[0] &&
    r2 === state.wantedTileRange[1] &&
    c1 === state.wantedTileRange[2] &&
    c2 === state.wantedTileRange[3]
  ) {
    // no-op: don't modify state spuriously, because useTiles() caller would re-render
    return state
  }

  const sparseTileGrid = splitGapsIntoLoadingTiles(state.sparseTileGrid, r1, r2)
  const wantedTileRange = [r1, r2, c1, c2]
  return {
    ...state,
    sparseTileGrid,
    wantedTileRange,
    loadingTile:
      state.loadingTile ||
      findWantedLoadingTile(sparseTileGrid, ...wantedTileRange)
  }
}

function reducer (state, action) {
  switch (action.type) {
    case 'handleFetchSuccess':
      return handleFetchSuccess(state, action.payload)
    case 'handleFetchError':
      return handleFetchError(state, action.payload)
    case 'setWantedTileRange':
      return handleSetWantedTileRange(state, ...action.payload)
    default:
      throw new Error('unknown action')
  }
}

/**
 * Load data for use in a table.
 *
 * Usage:
 *
 *     function MyTable(props) {
 *       const { sparseTileGrid, setWantedTileRange, isLoading } = useTiles({
 *         fetchTile, nTileRows, nTileColumns
 *       })
 *       return (
 *         <table>
 *           <tbody>
 *             {sparseTileGrid.map((tileColumns, tileRow) => (
 *               <tr key={tileRow}>
 *                 {tileRow.map((tile, tileColumn) => (
 *                   <td className={`tile-${tile.state}`} key={tileColumn} />
 *                 ))}
 *               </tr>
 *             ))}
 *           </tbody>
 *         </table>
 *       )
 *     }
 *
 * The return values are:
 *
 * * `sparseTileGrid` - Array of Array[Tile]|Number. Empty only if the table has no rows.
 *                      Each child Array is guaranteed to have length=`tileColumns`. A
 *                      Tile can be an Array[Array[Any]] (data), null (meaning "loading"),
 *                      or an object representing an error.
 * * `setWantedTileRange(r1, r2, c1, c2)` - Callback that suggests the next tiles to
 *                                          load. The caller is expected to call this
 *                                          when the user stops scrolling. The caller
 *                                          cannot "force" any requests: it can only
 *                                          say it's looking at these tiles and trust
 *                                          that tiles will be forthcoming. r2 and c2
 *                                          are "end" indexes in the C sense: they
 *                                          come _after_ the tile in question. So
 *                                          `0, 1, 2, 3` will only fetch tile (0,2).
 * * `isLoading` - True when any tile is a "loading" tile.
 */
export default function useTiles (props) {
  const { fetchTile, nTileRows, nTileColumns } = props
  const [{ sparseTileGrid, loadingTile }, dispatch] = useReducer(
    reducer,
    { nTileRows, nTileColumns },
    init
  )
  const isLoading = loadingTile !== null
  const setWantedTileRange = useCallback(
    (...payload) => dispatch({ type: 'setWantedTileRange', payload }),
    [dispatch]
  )

  useEffect(() => {
    if (loadingTile === null) return

    // call fetchTile() from useEffect(), not from reducer. Reducers should not
    // have side effects.
    const { tileRow, tileColumn } = loadingTile

    const abortController = new global.AbortController()
    const { signal } = abortController
    const currentFetch = fetchTile(tileRow, tileColumn, { signal })

    currentFetch.then(
      async response => {
        if (abortController.signal.aborted) return

        if (response.status !== 200) {
          return dispatch({
            type: 'handleFetchError',
            payload: {
              tileRow,
              tileColumn,
              error: {
                type: 'httpStatusNotOk',
                httpStatus: `${response.status} ${response.statusText}`
              }
            }
          })
        }

        let data
        try {
          data = await response.json()
        } catch ({ name, message }) {
          // XXX ...should we do anything if abortController.signal.aborted?
          return dispatch({
            type: 'handleFetchError',
            payload: {
              tileRow,
              tileColumn,
              error: { type: 'jsonError', error: { name, message } }
            }
          })
        }

        return dispatch({
          type: 'handleFetchSuccess',
          payload: { tileRow, tileColumn, rows: data.rows }
        })
      },
      ({ name, message }) => {
        if (abortController.signal.aborted) return

        dispatch({
          type: 'handleFetchError',
          payload: {
            tileRow,
            tileColumn,
            error: { type: 'fetchError', error: { name, message } }
          }
        })
      }
    )
    return () => abortController.abort()
  }, [loadingTile, fetchTile, dispatch])

  return { sparseTileGrid, setWantedTileRange, isLoading }
}
