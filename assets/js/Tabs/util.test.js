import { generateTabName } from './util'

describe('generateTabName', () => {
  const fn = generateTabName

  it('should generate a name', () => {
    const ret = fn(/Tab (\d+)/, 'Tab %d', [])
    expect(ret).toEqual('Tab 1')
  })

  it('should generate a name higher than all other matching names', () => {
    const ret = fn(/Tab (\d+)/, 'Tab %d', [ 'Tab 1', 'Tab 3' ])
    expect(ret).toEqual('Tab 4')
  })
})
