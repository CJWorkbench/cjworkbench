import { moduleParamsBuilders } from './UpdateTableAction'

const func = moduleParamsBuilders.editcells

describe('Edit Cell actions', () => {
  const Edit1 = { row: 3, col: 'foo', value: 'bar' }
  const Edit2 = { row: 10, col: 'bar', value: 'yippee!' }
  const Edit3 = { row: 3, col: 'foo', value: 'new!' }

  it('adds edit to existing Edit Cell module', () => {
    const ret = func({ celledits: [ Edit1 ] }, Edit2)
    expect(ret).toEqual({ celledits: [ Edit1, Edit2 ] })
  })

  it('replaces edit in an existing Edit Cell module', () => {
    const ret = func({ celledits: [ Edit1, Edit2 ] }, Edit3)
    expect(ret).toEqual({ celledits: [ Edit3, Edit2 ] })
  })
})
