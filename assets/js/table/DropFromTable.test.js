import { moduleParamsBuilders } from './UpdateTableAction'

const func = moduleParamsBuilders.selectcolumns

describe("DropFromTable actions", () => {
  it('adds new select module after the given module and sets column parameter', () => {
    const ret = func(null, { columnKey: 'A', drop_or_keep: 0 })
    expect(ret).toEqual({ colnames: 'A', drop_or_keep: 0 })
  })

  it('removes column when keeping', () => {
    const ret = func({ colnames: 'A,B', drop_or_keep: 1 }, { columnKey: 'A', drop_or_keep: 0 })
    expect(ret).toEqual({ colnames: 'B', drop_or_keep: 1 })
  })

  it('removes nothing when dropping a non-kept column', () => {
    const ret = func({ colnames: 'A,B', drop_or_keep: 1 }, { columnKey: 'C', drop_or_keep: 0 })
    expect(ret).toBe(null)
  })

  it('removes column when dropping', () => {
    const ret = func({ colnames: 'A,B', drop_or_keep: 0 }, { columnKey: 'C', drop_or_keep: 0 })
    expect(ret).toEqual({ colnames: 'A,B,C', drop_or_keep: 0 })
  })

  it('removes nothing when dropping a dropped column', () => {
    const ret = func({ colnames: 'A,B', drop_or_keep: 0 }, { columnKey: 'A', drop_or_keep: 0 })
    expect(ret).toBe(null)
  })

  it('creates empty module', () => {
    const ret = func(null, {})
    expect(ret).toEqual({})
  })
})
