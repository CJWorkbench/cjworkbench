/* eslint no-template-curly-in-string: 0 */
/* globals describe, expect, it */
import { shallow } from 'enzyme'
import { columnToCellFormatter } from './CellFormatters'

describe('NumberCellFormatter', () => {
  describe('default formatter', () => {
    const Formatter = columnToCellFormatter({ type: 'number', format: '{:,}' })
    const wrapper = (value) => shallow(<Formatter value={value} />)

    it('renders integers with numberFormat', () => {
      const w = wrapper(1234)
      expect(w.text()).toEqual('1,234')
    })

    it('renders floats with numberFormat', () => {
      const w = wrapper(1234.678)
      expect(w.text()).toEqual('1,234.678')
    })

    it('renders className=cell-number', () => {
      const w = wrapper(1)
      expect(w.find('.cell-number')).toHaveLength(1)
    })

    it('renders null as null', () => {
      const w = wrapper(null)
      expect(w.find('.cell-null.cell-number')).toHaveLength(1)
    })

    it('does not crash on text input', () => {
      // Sometimes, ReactDataGrid sends "new" values to "stale" formatters.
      // That's fine -- just don't crash or log a warning.
      const w = wrapper('three')
      expect(w.text()).toEqual('NaN')
    })
  })

  it('renders floats with prefix and suffix', () => {
    const Formatter = columnToCellFormatter({ type: 'number', format: '${:,.2f}!' })
    const wrapper = (value) => shallow(<Formatter value={value} />)
    const w = wrapper(1234.567)
    expect(w.text()).toEqual('$1,234.57!')
    expect(w.find('.number-value').text()).toEqual('1,234.57')
    expect(w.find('.number-prefix').text()).toEqual('$')
    expect(w.find('.number-suffix').text()).toEqual('!')
  })

  it('renders percentage of floats with numberFormat, with "%" as a suffix', () => {
    const Formatter = columnToCellFormatter({ type: 'number', format: '{:,.1%}!' })
    const wrapper = (value) => shallow(<Formatter value={value} />)
    const w = wrapper(12.3456)
    expect(w.text()).toEqual('1,234.6%!')
    expect(w.find('.number-value').text()).toEqual('1,234.6')
    expect(w.find('.number-suffix').text()).toEqual('%!')
  })

  it('renders invalid format as default, "{:,}"', () => {
    // Saw this in production on 2019-04-05 -- same day we deployed type
    // formatting for the first time.

    const Formatter = columnToCellFormatter({ type: 'number', format: '{:nope' })
    const wrapper = (value) => shallow(<Formatter value={value} />)
    const w = wrapper(1234.5678)
    expect(w.text()).toEqual('1,234.5678')
  })
})

describe('TextCellFormatter', () => {
  const Formatter = columnToCellFormatter({ type: 'text' })
  const wrapper = (value) => shallow(<Formatter value={value} />)

  it('renders the text', () => {
    const w = wrapper('hi')
    expect(w.text()).toEqual('hi')
  })

  it('renders className=cell-text', () => {
    const w = wrapper('hi')
    expect(w.find('.cell-text')).toHaveLength(1)
  })

  it('renders null as null', () => {
    const w = wrapper(null)
    expect(w.find('.cell-null.cell-text')).toHaveLength(1)
  })

  it('does not crash on numeric input', () => {
    // Sometimes, ReactDataGrid sends "new" values to "stale" formatters.
    // That's fine -- just don't crash or log a warning.
    const w = wrapper(3)
    expect(w.text()).toEqual('3')
  })

  it('only displays first line plus ellipsis if there are multiple lines', () => {
    // relates to https://www.pivotaltracker.com/story/show/159269958
    // We use CSS to preserve whitespace, and we use 'pre' because we
    // don't want to wrap. But we also don't want to try and fit
    // multiple lines of text into one line; and we want CSS's ellipsize
    // code to work.
    //
    // So here it is:
    // whitespace: pre -- preserves whitespace, never wraps
    // text-overflow: ellipsis -- handles single line too long
    // adding ellipsis (what we're testing here) -- handles multiple lines
    const text = '  Veni \r\r\n\n\u2029 Vi\t\vdi  \f  Vici'
    const w = wrapper(text)
    expect(w.text()).toEqual('  Veni ↵↵↵¶ Vi\t⭿di  ↡  Vici')
    expect(w.prop('title')).toEqual(text) // for when the user hovers
  })
})

describe('TimestampCellFormatter', () => {
  const Formatter = columnToCellFormatter({ type: 'timestamp' })
  const wrapper = (value) => shallow(<Formatter value={value} />)

  it('renders with millisecond precision', () => {
    const w = wrapper('2018-08-29T18:34:01.002Z')
    expect(w.text()).toEqual('2018-08-29T18:34:01.002Z')
  })

  it('renders with second precision', () => {
    const w = wrapper('2018-08-29T18:34:01.000Z')
    expect(w.text()).toEqual('2018-08-29T18:34:01Z')
  })

  it('renders with minute precision', () => {
    const w = wrapper('2018-08-29T18:34:00.000Z')
    expect(w.text()).toEqual('2018-08-29T18:34Z')
  })

  it('renders with year precision', () => {
    const w = wrapper('2018-08-29T00:00:00.000Z')
    expect(w.text()).toEqual('2018-08-29')
  })

  it('renders className=cell-timestamp', () => {
    const w = wrapper('2018-08-29T00:00:00.000Z')
    expect(w.find('.cell-timestamp')).toHaveLength(1)
  })

  it('renders null as null', () => {
    const w = wrapper(null)
    expect(w.find('.cell-null.cell-timestamp')).toHaveLength(1)
  })

  it('does not crash on string input', () => {
    // ReactDataGrid erroneously feeds us wrongly-typed values sometimes.
    const w = wrapper('hi')
    expect(w.find('*')).toHaveLength(0)
  })
})
