import { moduleParamsBuilders } from './UpdateTableAction'

const func = moduleParamsBuilders['sort']

describe("Sort actions", () => {
  it('adds new sort module', () => {
    const ret = func(null, { columnKey: 'A', direction: 1 })
    expect(ret).toEqual({ column: 'A', direction: 1 })
  })

  it('sets existing sort parameters', () => {
    const ret = func({ column: 'B', direction: 1 }, { columnKey: 'A', direction: 0 })
    expect(ret).toEqual({ column: 'A', direction: 0 })
  })

  it('returns null when all is the same', () => {
    const ret = func({ column: 'B', direction: 1 }, { columnKey: 'B', direction: 1 })
    expect(ret).toBe(null)
  })
})
