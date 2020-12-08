/* globals describe, expect, it, jest */
import React from 'react'
import { act } from 'react-dom/test-utils'
import WorkflowContextMenu from './WorkflowContextMenu'
import { mountWithI18n } from '../i18n/test-utils'

describe('WorkflowContextMenu', () => {
  const wrapper = (extraProps = {}) => mountWithI18n(
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

  it('deletes workflow', async () => {
    const w = wrapper()
    w.find('button').simulate('click') // open menu
    await act(async () => await null) // Popper update() - https://github.com/popperjs/react-popper/issues/350
    w.find('button.delete-workflow').simulate('click')
    expect(w.prop('deleteWorkflow')).toHaveBeenCalledWith(3)
  })

  it('duplicates workflow', async () => {
    const w = wrapper()
    w.find('button').simulate('click') // open menu
    await act(async () => await null) // Popper update() - https://github.com/popperjs/react-popper/issues/350
    w.find('button.duplicate-workflow').simulate('click')
    expect(w.prop('duplicateWorkflow')).toHaveBeenCalledWith(3)
  })

  it('should not render a delete button', async () => {
    const w = wrapper({ deleteWorkflow: null })
    w.find('button').simulate('click') // open menu
    await act(async () => await null) // Popper update() - https://github.com/popperjs/react-popper/issues/350
    expect(w.find('button.delete-workflow')).toHaveLength(0)
  })
})
