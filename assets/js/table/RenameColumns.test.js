/* globals describe, expect, it */
import { moduleParamsBuilders } from './UpdateTableAction'

const func = moduleParamsBuilders.renamecolumns

describe('RenameColumns actions', () => {
  it('adds a new rename module', () => {
    const ret = func(null, { prevName: 'A', newName: 'B' }, false)
    expect(ret).toEqual({ renames: { A: 'B' } })
  })

  it('adds a new column to an existing rename module', () => {
    const ret = func({ renames: { A: 'B' } }, { prevName: 'B', newName: 'C' }, true)
    expect(ret).toEqual({ renames: { A: 'B', B: 'C' } })
  })

  it('renames an already-renamed column from the previous table', () => {
    const ret = func({ renames: { A: 'B' } }, { prevName: 'A', newName: 'C' }, true)
    expect(ret).toEqual({ renames: { A: 'C' } })
  })

  it('resets a rename if renaming another column to that name from the previous table', () => {
    const ret = func({ renames: { A: 'B' } }, { prevName: 'C', newName: 'B' }, true)
    expect(ret).toEqual({ renames: { C: 'B' } })
  })

  it('renames an already-renamed column from the current table', () => {
    const ret = func({ renames: { A: 'B' } }, { prevName: 'B', newName: 'C' }, false)
    expect(ret).toEqual({ renames: { A: 'C' } })
  })

  it('resets a rename if renaming another column to that name from the current table', () => {
    const ret = func({ renames: { A: 'B' } }, { prevName: 'C', newName: 'B' }, false)
    expect(ret).toEqual({ renames: { C: 'B' } })
  })
})
