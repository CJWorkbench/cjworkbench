/* globals expect, test */
import { LoadedTile, LoadingTile, SparseTileGrid } from './tiles'
import splitGapsIntoLoadingTiles from './splitGapsIntoLoadingTiles'

test('returns input when no gaps impact us', () => {
  const sparseTileGrid = new SparseTileGrid([
    [new LoadedTile(0, 0, [['0']])],
    3,
    [new LoadedTile(4, 0, [['4']])],
    [new LoadingTile(5, 0)],
    [new LoadedTile(5, 0, [['6']])],
    2,
    [new LoadedTile(9, 0, [['9']])]
  ])
  const result = splitGapsIntoLoadingTiles(sparseTileGrid, 4, 6)
  expect(result).toBe(sparseTileGrid)
})

test('splits a gap at its start', () => {
  const sparseTileGrid = new SparseTileGrid([
    [new LoadedTile(0, 0, [['0']])],
    4
  ])
  const result = splitGapsIntoLoadingTiles(sparseTileGrid, 1, 3)
  expect(result).toEqual(new SparseTileGrid([
    [new LoadedTile(0, 0, [['0']])],
    [new LoadingTile(1, 0)],
    [new LoadingTile(2, 0)],
    2
  ]))
})

test('splits a gap at its end', () => {
  const sparseTileGrid = new SparseTileGrid([
    [new LoadedTile(0, 0, [['0']])],
    4,
    [new LoadedTile(5, 0, [['5']])]
  ])
  const result = splitGapsIntoLoadingTiles(sparseTileGrid, 3, 5)
  expect(result).toEqual(new SparseTileGrid([
    [new LoadedTile(0, 0, [['0']])],
    2,
    [new LoadingTile(3, 0)],
    [new LoadingTile(4, 0)],
    [new LoadedTile(5, 0, [['5']])]
  ]))
})

test('splits a gap in its middle', () => {
  const sparseTileGrid = new SparseTileGrid([
    [new LoadedTile(0, 0, [['0']])],
    4,
    [new LoadedTile(5, 0, [['5']])]
  ])
  const result = splitGapsIntoLoadingTiles(sparseTileGrid, 2, 4)
  expect(result).toEqual(new SparseTileGrid([
    [new LoadedTile(0, 0, [['0']])],
    1,
    [new LoadingTile(2, 0)],
    [new LoadingTile(3, 0)],
    1,
    [new LoadedTile(5, 0, [['5']])]
  ]))
})

test('splits an end-gap at its end, leaving a number before', () => {
  const sparseTileGrid = new SparseTileGrid([
    [new LoadedTile(0, 0, [['0']])],
    4,
  ])
  const result = splitGapsIntoLoadingTiles(sparseTileGrid, 3, 5)
  expect(result).toEqual(new SparseTileGrid([
    [new LoadedTile(0, 0, [['0']])],
    2,
    [new LoadingTile(3, 0)],
    [new LoadingTile(4, 0)],
  ]))
})

test('splits an end-gap completely', () => {
  const sparseTileGrid = new SparseTileGrid([
    [new LoadedTile(0, 0, [['0']])],
    2,
  ])
  const result = splitGapsIntoLoadingTiles(sparseTileGrid, 1, 3)
  expect(result).toEqual(new SparseTileGrid([
    [new LoadedTile(0, 0, [['0']])],
    [new LoadingTile(1, 0)],
    [new LoadingTile(2, 0)],
  ]))
})

test('splits an end-gap completely, even when wanted start overlaps', () => {
  const sparseTileGrid = new SparseTileGrid([
    [new LoadedTile(0, 0, [['0']])],
    2,
  ])
  const result = splitGapsIntoLoadingTiles(sparseTileGrid, 0, 3)
  expect(result).toEqual(new SparseTileGrid([
    [new LoadedTile(0, 0, [['0']])],
    [new LoadingTile(1, 0)],
    [new LoadingTile(2, 0)],
  ]))
})
