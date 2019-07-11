import React from 'react'
import WorkflowContextMenu from './WorkflowContextMenu'
import { mount } from 'enzyme'

describe('WorkflowContextMenu', () => {
  const wrapper = (extraProps = {}) => mount(
    <WorkflowContextMenu
      workflowId={3}
      deleteWorkflow={jest.fn()}
      duplicateWorkflow={jest.fn()}
      {...extraProps}
    />
  )

  it('renders correctly', () => {
    expect(wrapper()).toMatchSnapshot()
  })

  it('deletes workflow', () => {
    const w = wrapper()
    w.find('button').simulate('click') // open menu
    w.find('button.delete-workflow').simulate('click')
    expect(w.prop('deleteWorkflow')).toHaveBeenCalledWith(3)
  })

  it('duplicates workflow', () => {
    const w = wrapper()
    w.find('button').simulate('click') // open menu
    w.find('button.duplicate-workflow').simulate('click')
    expect(w.prop('duplicateWorkflow')).toHaveBeenCalledWith(3)
  })

  it('should not render a delete button', () => {
    const w = wrapper({ deleteWorkflow: null })
    w.find('button').simulate('click') // open menu
    expect(w.find('button.delete-workflow')).toHaveLength(0)
  })
})
