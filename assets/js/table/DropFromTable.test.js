/* globals describe, expect, it */
import { moduleParamsBuilders } from './UpdateTableAction'

const func = moduleParamsBuilders.selectcolumns

describe('DropFromTable actions', () => {
  it('adds new select module after the given module and sets column parameter', () => {
    const ret = func(null, { columnKey: 'A', keep: false })
    expect(ret).toEqual({ colnames: ['A'], keep: false })
  })

  it('removes column when keeping', () => {
    const ret = func(
      { colnames: ['A', 'B'], keep: true },
      { columnKey: 'A', keep: false }
    )
    expect(ret).toEqual({ colnames: ['B'], keep: true })
  })

  it('removes nothing when dropping a non-kept column', () => {
    const ret = func(
      { colnames: ['A', 'B'], keep: true },
      { columnKey: 'C', keep: false }
    )
    expect(ret).toBe(null)
  })

  it('removes column when dropping', () => {
    const ret = func(
      { colnames: ['A', 'B'], keep: false },
      { columnKey: 'C', keep: false }
    )
    expect(ret).toEqual({ colnames: ['A', 'B', 'C'], keep: false })
  })

  it('removes nothing when dropping a dropped column', () => {
    const ret = func(
      { colnames: ['A', 'B'], keep: false },
      { columnKey: 'A', keep: false }
    )
    expect(ret).toBe(null)
  })

  it('creates empty module', () => {
    const ret = func(null, {})
    expect(ret).toEqual({})
  })
})
