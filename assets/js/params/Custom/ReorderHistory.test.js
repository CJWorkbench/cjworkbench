import React from 'react'
import { ReorderHistory } from './ReorderHistory'
import { shallow } from 'enzyme'

describe('ReorderHistory', () => {
  it('renders with empty history', () => {
    const tree = shallow(
      <ReorderHistory value={[]} />
    )
    expect(tree.find('.reorder-idx')).toHaveLength(0)
    expect(tree.find('.reorder-column')).toHaveLength(0)
    expect(tree.find('.reorder-from')).toHaveLength(0)
    expect(tree.find('.reorder-to')).toHaveLength(0)
  })

  it('renders history properly', () => {
    const history = [
      {
        'column': 'maze',
        'from': 0, // A
        'to': 2 // C
      },
      {
        'column': 'door',
        'from': 26, // AA
        'to': 1 // B
      }
    ]
    const tree = shallow(<ReorderHistory value={history} />)
    expect(tree.find('.reorder-idx')).toHaveLength(2)
    expect(parseInt(tree.find('.reorder-idx').get(0).props.children)).toEqual(1)
    expect(parseInt(tree.find('.reorder-idx').get(1).props.children)).toEqual(2)

    expect(tree.find('.reorder-column')).toHaveLength(2)
    expect(tree.find('.reorder-column').get(0).props.children).toEqual('maze')
    expect(tree.find('.reorder-column').get(1).props.children).toEqual('door')

    expect(tree.find('.reorder-from')).toHaveLength(2)
    expect(tree.find('.reorder-from').get(0).props.children).toEqual('A')
    expect(tree.find('.reorder-from').get(1).props.children).toEqual('AA')

    expect(tree.find('.reorder-to')).toHaveLength(2)
    expect(tree.find('.reorder-to').get(0).props.children).toEqual('C')
    expect(tree.find('.reorder-to').get(1).props.children).toEqual('B')
  })
})
