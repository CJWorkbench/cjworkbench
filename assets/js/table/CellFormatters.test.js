/* eslint no-template-curly-in-string: 0 */
/* globals describe, expect, it */
import { mount } from 'enzyme'
import { columnToCellFormatter } from './CellFormatters'

describe('NumberCellFormatter', () => {
  describe('default formatter', () => {
    const Formatter = columnToCellFormatter({ type: 'number', format: '{:,}' })
    const wrapper = value => mount(<Formatter value={value} />)

    it('does not crash on text input', () => {
      // Sometimes, ReactDataGrid sends "new" values to "stale" formatters.
      // That's fine -- just don't crash or log a warning.
      const w = wrapper('three')
      expect(w.text()).toEqual('')
    })
  })
})

describe('TextCellFormatter', () => {
  const Formatter = columnToCellFormatter({ type: 'text' })
  const wrapper = value => mount(<Formatter value={value} />)

  it('does not crash on numeric input', () => {
    // Sometimes, ReactDataGrid sends "new" values to "stale" formatters.
    // That's fine -- just don't crash or log a warning.
    const w = wrapper(3)
    expect(w.text()).toEqual('')
  })
})

describe('TimestampCellFormatter', () => {
  const Formatter = columnToCellFormatter({ type: 'timestamp' })
  const wrapper = value => mount(<Formatter value={value} />)

  it('does not crash on string input', () => {
    // ReactDataGrid erroneously feeds us wrongly-typed values sometimes.
    const w = wrapper('hi')
    expect(w.text()).toEqual('hi')
  })
})
