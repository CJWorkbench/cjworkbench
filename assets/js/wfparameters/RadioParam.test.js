import React from 'react'
import { mount } from 'enzyme'

import RadioParam from './RadioParam';

describe('RadioButtons', () => {
  const wrapper = (extraProps = {}) => mount(
    <RadioParam
      name='radio-buttons'
      items='Apple|Kittens|Banana'
      selectedIdx={0}
      onChange={jest.fn()}
      {...extraProps}
    />
  )
  it('renders correctly', () => {
    const w = wrapper({isReadOnly: true})
    expect(wrapper).toMatchSnapshot();
  });

  it('radio renders number of buttons correctly', () => {
    const w = wrapper({isReadOnly: false});
    expect(w.find('input[type="radio"]')).toHaveLength(3)
  });

  it('returns correct value when clicked', () => {
    const w = wrapper({isReadOnly: false});
    w.find('input[value="2"]').simulate('change')
    expect(w.prop('onChange')).toHaveBeenCalledWith('2')
  });

  it('should be disabled when read only', () => {
    let items = 'Apple|Kittens|Banana'.split('|')
    const w = wrapper({isReadOnly: true});
    for (let item in items) {
      let button = w.find(('input[value="' + item + '"]'))
      expect(button.prop('disabled')).toEqual(true)
    }
  });
})
