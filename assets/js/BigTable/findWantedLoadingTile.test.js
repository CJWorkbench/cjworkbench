/* globals expect, test */
import findWantedLoadingTile from './findWantedLoadingTile'
import { LoadingTile, LoadedTile, SparseTileGrid } from './tiles'

test('find null on empty grid', () => {
  expect(findWantedLoadingTile(new SparseTileGrid([]), 0, 1, 0, 1)).toBe(null)
})

test('find the first tile on a one-tile grid', () => {
  expect(findWantedLoadingTile(new SparseTileGrid([[new LoadingTile(0, 0)]]), 0, 1, 0, 1)).toEqual(new LoadingTile(0, 0))
})

test('find nothing when the grid is all loaded', () => {
  expect(findWantedLoadingTile(new SparseTileGrid([[new LoadedTile(0, 0, [['X']])]], 0, 1, 0, 1))).toBe(null)
})

test('skip gaps', () => {
  expect(findWantedLoadingTile(new SparseTileGrid([
    [new LoadingTile(0, 0), new LoadingTile(0, 1), new LoadingTile(0, 2)],
    1,
    [new LoadingTile(2, 0), new LoadingTile(2, 1), new LoadingTile(2, 2)],
  ]), 2, 3, 1, 2)).toEqual(new LoadingTile(2, 1))
})

test('find the first loading tile in a row', () => {
  expect(findWantedLoadingTile(new SparseTileGrid([
    [new LoadingTile(0, 0), new LoadedTile(0, 1, [['C1']]), new LoadedTile(0, 2, [['D1']]), new LoadingTile(0, 3)],
  ]), 0, 1, 1, 4)).toEqual(new LoadingTile(0, 3))
})

test('skip an all-loaded row and search the next row', () => {
  expect(findWantedLoadingTile(new SparseTileGrid([
    [new LoadingTile(0, 0), new LoadedTile(0, 1, [['C1']]), new LoadedTile(0, 2, [['D1']]), new LoadedTile(0, 3, [['E1']])],
    [new LoadingTile(1, 0), new LoadedTile(1, 1, [['C1']]), new LoadingTile(1, 2), new LoadedTile(1, 3, [['E2']])],
  ]), 0, 2, 1, 4)).toEqual(new LoadingTile(1, 2))
})
