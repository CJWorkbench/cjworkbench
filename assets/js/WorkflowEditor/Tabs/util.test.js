/* globals describe, expect, it */
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

  it('should generate a name with a different pattern', () => {
    const ret = fn(/A \((\d+)\)/, 'A (%d)', [ 'A', 'A (3)' ])
    expect(ret).toEqual('A (4)')
  })

  it('should allow escaping % symbol', () => {
    const ret = fn(/%d%%d (\d+)/, '%%d%%%%d %d', [ '%d%%d 1' ])
    expect(ret).toEqual('%d%%d 2')
  })
})
