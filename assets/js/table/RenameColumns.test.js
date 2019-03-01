import { moduleParamsBuilders } from './UpdateTableAction'

const func = moduleParamsBuilders['renamecolumns']

describe('RenameColumns actions', () => {
  it('adds a new rename module', () => {
    const ret = func(null, { prevName: 'A', newName: 'B' })
    expect(ret).toEqual({ renames: { A: 'B' } })
  })

  it('adds a new column to an existing rename module', () => {
    const ret = func({ renames: { 'A': 'B' } }, { prevName: 'B', newName: 'C' })
    expect(ret).toEqual({ renames: { A: 'B', B: 'C' } })
  })

  it('renames an already-renamed column', () => {
    const ret = func({ renames: { 'A': 'B' } }, { prevName: 'A', newName: 'C' })
    expect(ret).toEqual({ renames: { A: 'C' } })
  })
})
