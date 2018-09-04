import React from 'react'
import { shallow } from 'enzyme'
import { RowIndexFormatter, DatetimeCellFormatter, NumberCellFormatter, TextCellFormatter } from './DataGrid'

describe('RowIndexFormatter', () => {
  const wrapper = (value) => shallow(<RowIndexFormatter value={value} />)

  it('renders number of digits in class name', () => {
    const w1 = wrapper(4)
    const w2 = wrapper(10)
    const w3 = wrapper(100)

    expect(w1.find('.row-number.row-number-1')).toHaveLength(1)
    expect(w2.find('.row-number.row-number-2')).toHaveLength(1)
    expect(w3.find('.row-number.row-number-3')).toHaveLength(1)
  })

  it('does not add commas on long numbers', () => {
    const w = wrapper(1234567)
    expect(w.text()).toEqual('1234567')
  })
})

describe('NumberCellFormatter', () => {
  const wrapper = (value) => shallow(<NumberCellFormatter value={value} />)
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
    expect(w.find('.cell-null').text()).toEqual('null')
  })

  it('does not crash on text input', () => {
    // Sometimes, ReactDataGrid sends "new" values to "stale" formatters.
    // That's fine -- just don't crash or log a warning.
    const w = wrapper('three')
    expect(w.text()).toEqual('NaN')
  })
})

describe('TextCellFormatter', () => {
  const wrapper = (value) => shallow(<TextCellFormatter value={value} />)

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
    expect(w.find('.cell-null').text()).toEqual('null')
  })

  it('does not crash on numeric input', () => {
    // Sometimes, ReactDataGrid sends "new" values to "stale" formatters.
    // That's fine -- just don't crash or log a warning.
    const w = wrapper(3)
    expect(w.text()).toEqual('3')
  })
})

describe('DatetimeCellFormatter', () => {
  const wrapper = (value) => shallow(<DatetimeCellFormatter value={value} />)

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
    expect(w.find('.cell-null').text()).toEqual('null')
  })

  it('does not crash on string input', () => {
    // ReactDataGrid erroneously feeds us wrongly-typed values sometimes.
    const w = wrapper('hi')
    expect(w.find('*')).toHaveLength(0)
  })
})
