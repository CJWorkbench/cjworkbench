/* globals expect, test */
import { LoadedTile, LoadingTile, ErrorTile, SparseTileGrid } from './tiles'
import placeTile from './placeTile'

test('replace first LoadingTile with LoadedTile', () => {
  const loadedTile = new LoadedTile(0, 0, [['foo', 'bar']])
  expect(
    placeTile(new SparseTileGrid([[new LoadingTile(0, 0, 2, 1)]]), loadedTile)
  ).toEqual(new SparseTileGrid([[loadedTile]]))
})

test('replace a LoadingTile with an ErrorTile', () => {
  const errorTile = new ErrorTile(0, 0, 2, 1, 'message')
  expect(
    placeTile(new SparseTileGrid([[new LoadingTile(0, 0, 2, 1)]]), errorTile)
  ).toEqual(new SparseTileGrid([[errorTile]]))
})

test('replace middle LoadingTile with LoadedTile', () => {
  const A1 = new LoadedTile(0, 0, [['foo', 'bar']])
  const B1 = new LoadedTile(0, 1, [['bar', 'baz']])
  const C1 = new LoadedTile(0, 2, [['baz', 'moo']])
  const A2 = new LoadedTile(1, 0, [['Foo', 'Bar']])
  const B2 = new LoadedTile(1, 1, [['Bar', 'Baz']])
  const C2 = new LoadedTile(1, 2, [['Baz', 'Moo']])
  const A3 = new LoadedTile(2, 0, [['FOo', 'BAr']])
  const B3 = new LoadingTile(2, 1, 1, 2)
  const C3 = new LoadedTile(2, 2, [['BAz', 'MOo']])
  const A4 = new LoadedTile(3, 0, [['FOO', 'BAR']])
  const B4 = new LoadedTile(3, 1, [['BAR', 'BAZ']])
  const C4 = new LoadedTile(3, 2, [['BAZ', 'MOO']])
  const row1 = [A1, B1, C1]
  const row2 = [A2, B2, C2]
  const row3 = [A3, B3, C3]
  const row4 = [A4, B4, C4]
  const newB3 = new LoadedTile(2, 1, [['BAr', 'BAz']])
  const result = placeTile(new SparseTileGrid([row1, row2, row3, row4]), newB3)
  expect(result).toEqual(new SparseTileGrid([row1, row2, [A3, newB3, C3], row4]))
  // We'll test rows for "is", not "equals". Unchanged rows shouldn't re-render.
  expect(result.tileRows[0]).toBe(row1)
  expect(result.tileRows[1]).toBe(row2)
  expect(result.tileRows[3]).toBe(row4)
})

test('skip a RowGapTile', () => {
  const A1 = new LoadedTile(0, 0, [['foo', 'bar']])
  const B1 = new LoadedTile(0, 1, [['bar', 'baz']])
  const A4 = new LoadedTile(3, 0, [['FOO', 'BAR']])
  const B4 = new LoadingTile(3, 1, 1, 2)
  const newB4 = new LoadedTile(3, 1, [['BAR', 'BAZ']])

  const result = placeTile(new SparseTileGrid([[A1, B1], 2, [A4, B4]]), newB4)
  expect(result).toEqual(new SparseTileGrid([[A1, B1], 2, [A4, newB4]]))
})
