import React from 'react'
import OAuth  from './OAuth'
import { mount } from 'enzyme'
import { store,  getCurrentUserAction, disconnectCurrentUserAction } from '../../workflow-reducer';
jest.mock('../../workflow-reducer');

describe('OAuth', () => {
  const wrapper = (extraProps) => {
    return mount(
      <OAuth
        name='x'
        startCreateSecret={jest.fn()}
        deleteSecret={jest.fn()}
        secret={{name: 'a secret'}}
        secretLogic={{service: 'google'}}
        {...extraProps}
        />
    )
  }

  it('matches snapshot', () => {
    const w = wrapper({})
    expect(w).toMatchSnapshot()
  })

  it('renders without a secret', () => {
    const w = wrapper({ secret: null })
    expect(w.find('button.connect')).toHaveLength(1)
    w.find('button.connect').simulate('click')
    expect(w.prop('startCreateSecret')).toHaveBeenCalledWith('x')
  })

  it('disconnects', () => {
    const w = wrapper({ secret: { name: 'foo@example.org' } })
    w.find('button.disconnect').simulate('click')
    expect(w.prop('deleteSecret')).toHaveBeenCalledWith('x')
  })
})
