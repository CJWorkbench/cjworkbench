import { moduleParamsBuilders } from './UpdateTableAction'

const func = moduleParamsBuilders['renamecolumns']

describe('RenameColumns actions', () => {
  it('adds a new rename module', () => {
    const ret = func(null, { prevName: 'A', newName: 'B' })
    expect(ret).toEqual({ 'rename-entries': JSON.stringify({ A: 'B' }) })
  })

  it('adds a new column to an existing rename module', () => {
    const ret = func({ 'rename-entries': JSON.stringify({ 'A': 'B' }) }, { prevName: 'B', newName: 'C' })
    expect(ret).toEqual({ 'rename-entries': JSON.stringify({ A: 'B', B: 'C' }) })
  })

  it('renames an already-renamed column', () => {
    const ret = func({ 'rename-entries': JSON.stringify({ 'A': 'B' }) }, { prevName: 'A', newName: 'C' })
    expect(ret).toEqual({ 'rename-entries': JSON.stringify({ A: 'C' }) })
  })
})
