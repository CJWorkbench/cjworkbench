import React from 'react'
import WorkflowListNavBar from './WorkflowListNavBar'
import { shallow } from 'enzyme'

describe('WorkflowListNavBar', () => {
  it('Renders correctly', () => {
    const wrapper = shallow(<WorkflowListNavBar />)
    expect(wrapper).toMatchSnapshot()
  })
})
