import React from 'react'
import WorkflowMetadata from './WorkflowMetadata'
import { mount, ReactWrapper } from 'enzyme'
import { okResponseMock } from './test-utils'


describe('WorkflowMetadata', () => {
  const today = new Date('Fri Sep 22 2017 17:03:52 GMT-0400 (EDT)')
  const dayBefore = today.setDate(today.getDate() - 2)

  const defaultWorkflow = {
    id: 100,
    public: false,
    owner_name: "Harry Harrison",
    last_update: dayBefore,
    read_only: false
  }

  const wrapper = (extraProps={}, workflowExtraProps={}) => {
    const workflow = { ...defaultWorkflow, ...workflowExtraProps }
    return mount(
      <WorkflowMetadata
        workflow={workflow}
        test_now={today}
        onChangeIsPublic={jest.fn()}
      />
    )
  }

  it('renders private workflow correctly', () => {
    expect(wrapper({}, { public: false })).toMatchSnapshot()
  })

  it('converts from private to public', () => {
    const w = wrapper({}, { public: false })

    w.find('button[title="Change privacy"]').simulate('click')
    w.update()

    w.find('button[title="Make Public"]').simulate('click')
    expect(w.prop('onChangeIsPublic')).toHaveBeenCalledWith(defaultWorkflow.id, true)

    // Test that the modal disappears
    w.update()
    expect(w.find('button[title="Make Public"]')).toHaveLength(0)
  })

  it('converts from public to private', () => {
    const w = wrapper({}, { public: true })

    w.find('button[title="Change privacy"]').simulate('click')
    w.update()

    w.find('button[title="Make Private"]').simulate('click')
    expect(w.prop('onChangeIsPublic')).toHaveBeenCalledWith(defaultWorkflow.id, false)

    // Test that the modal disappears
    w.update()
    expect(w.find('button[title="Make Private"]')).toHaveLength(0)
  })
})
