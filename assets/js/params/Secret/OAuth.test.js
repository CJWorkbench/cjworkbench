import React from 'react'
import OAuth  from './OAuth'
import { mount } from 'enzyme'
import { store,  getCurrentUserAction, disconnectCurrentUserAction } from '../../workflow-reducer';
jest.mock('../../workflow-reducer');

describe('OAuth', () => {
  const wrapper = (extraProps) => {
    return mount(
      <OAuth
        paramIdName={'x'}
        startCreateSecret={jest.fn()}
        deleteSecret={jest.fn()}
        secretName={'a secret'}
        {...extraProps}
        />
    )
  }

  it('matches snapshot', () => {
    const w = wrapper({})
    expect(w).toMatchSnapshot()
  })

  it('renders without a secretName', () => {
    const w = wrapper({ secretName: null })
    expect(w.find('button.connect')).toHaveLength(1)
    w.find('button.connect').simulate('click')
    expect(w.prop('startCreateSecret')).toHaveBeenCalledWith('x')
  })

  it('disconnects', () => {
    const w = wrapper({ secretName: 'foo@example.org' })
    w.find('button.disconnect').simulate('click')
    expect(w.prop('deleteSecret')).toHaveBeenCalledWith('x')
  })
})
