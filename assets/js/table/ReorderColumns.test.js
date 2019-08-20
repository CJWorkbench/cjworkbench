/* globals describe, expect, it */
import { moduleParamsBuilders } from './UpdateTableAction'

const func = moduleParamsBuilders.reordercolumns

describe('ReorderColumns actions', () => {
  it('adds a new reorder module', () => {
    const ret = func(null, { column: 'A', from: 3, to: 0 })
    expect(ret).toEqual({ 'reorder-history': JSON.stringify([{ column: 'A', to: 0, from: 3 }]) })
  })

  it('updates a reorder module', () => {
    const ret = func({ 'reorder-history': JSON.stringify([{ column: 'A', from: 2, to: 0 }]) }, { column: 'B', from: 1, to: 2 })
    expect(ret).toEqual({ 'reorder-history': JSON.stringify([{ column: 'A', from: 2, to: 0 }, { column: 'B', to: 1, from: 1 }]) })
  })
})
