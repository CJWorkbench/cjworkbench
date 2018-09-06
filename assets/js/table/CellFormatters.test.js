import React from 'react'
import { shallow } from 'enzyme'
import { typeToCellFormatter } from './CellFormatters'

describe('NumberCellFormatter', () => {
  const Formatter = typeToCellFormatter('number')
  const wrapper = (value) => shallow(<Formatter value={value} />)
  const numberFormat = new Intl.NumberFormat() // different on different test platforms

  it('renders integers with numberFormat', () => {
    const w = wrapper(1234)
    expect(w.text()).toEqual(numberFormat.format(1234))
  })

  it('renders floats with numberFormat', () => {
    const w = wrapper(1234.678)
    expect(w.text()).toEqual(numberFormat.format(1234.678))
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

describe('TextCellFormatter', () => {
  const Formatter = typeToCellFormatter('text')
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
})

describe('DatetimeCellFormatter', () => {
  const Formatter = typeToCellFormatter('datetime')
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

  it('renders className=cell-datetime', () => {
    const w = wrapper('2018-08-29T00:00:00.000Z')
    expect(w.find('.cell-datetime')).toHaveLength(1)
  })

  it('renders null as null', () => {
    const w = wrapper(null)
    expect(w.find('.cell-null.cell-datetime')).toHaveLength(1)
  })

  it('does not crash on string input', () => {
    // ReactDataGrid erroneously feeds us wrongly-typed values sometimes.
    const w = wrapper('hi')
    expect(w.find('*')).toHaveLength(0)
  })
})
