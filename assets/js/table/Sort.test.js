import { moduleParamsBuilders } from './UpdateTableAction'

const func = moduleParamsBuilders['sort']

describe("Sort actions", () => {
  it('adds new sort module', () => {
    const ret = func(null, { columnKey: 'A', is_ascending: true })
    expect(ret).toEqual({ sort_columns: [{ colname: 'A', is_ascending: true }], keep_top: '' })
  })

  it('changes direction if existing params has same column first', () => {
    const ret = func({ sort_columns: [{ colname: 'A', is_ascending: true }], keep_top: '2' }, { columnKey: 'A', is_ascending: false })
    expect(ret).toEqual({ sort_columns: [{ colname: 'A', is_ascending: false }], keep_top: '2' })
  })

  it('returns null if existing params has same column first and direction', () => {
    const ret = func({ sort_columns: [{ colname: 'A', is_ascending: true }], keep_top: '2' }, { columnKey: 'A', is_ascending: true })
    expect(ret).toBe(null)
  })

  it('removes existing column and prepends to new param', () => {
    const ret = func(
      { sort_columns: [{ colname: 'A', is_ascending: true }, { colname: 'B', is_ascending: true }], keep_top: '' },
      { columnKey: 'B', is_ascending: true })
    expect(ret).toEqual({ sort_columns: [{ colname: 'B', is_ascending: true }, { colname: 'A', is_ascending: true }], keep_top: '' })
  })
})
