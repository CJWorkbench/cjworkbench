/* globals describe, expect, it */
import { shallow } from 'enzyme'
import RowActionsCell from './RowActionsCell'

describe('RowActionsCell', () => {
  const wrapper = (rowIdx) => shallow(<RowActionsCell rowIdx={rowIdx} />)

  it('renders number of digits in class name', () => {
    const w1 = wrapper(8)
    const w2 = wrapper(9)
    const w3 = wrapper(99)

    expect(w1.find('.row-number.row-number-1')).toHaveLength(1)
    expect(w2.find('.row-number.row-number-2')).toHaveLength(1)
    expect(w3.find('.row-number.row-number-3')).toHaveLength(1)
  })

  it('does not add commas on long numbers', () => {
    const w = wrapper(1234567)
    expect(w.text()).toEqual('1234568')
  })
})
