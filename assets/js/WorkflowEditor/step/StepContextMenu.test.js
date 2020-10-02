/* globals afterEach, beforeEach, describe, expect, it, jest */
import React from 'react'
import StepContextMenu from './StepContextMenu'
import { mountWithI18n } from '../../i18n/test-utils'

describe('StepContextMenu', () => {
  let wrapper
  let deleteStep

  beforeEach(() => {
    deleteStep = jest.fn()

    wrapper = mountWithI18n(
      <StepContextMenu
        deleteStep={deleteStep}
        id={415}
        className='menu-test-class'
      />
    )
  })

  afterEach(() => wrapper.unmount())

  it('should match snapshot', () => {
    expect(wrapper).toMatchSnapshot()
  })

  // only checking the call to deleteStep(), not the removal
  it('Renders menu option to Delete with onClick method', () => {
    // open the context menu
    wrapper.find('button.context-button').simulate('click')

    const deleteButton = wrapper.find('button.test-delete-button')
    expect(deleteButton).toHaveLength(1)
    deleteButton.simulate('click')
    expect(deleteStep).toHaveBeenCalled()
  })

  it('should open and close the export modal', () => {
    // open the context menu
    wrapper.find('button.context-button').simulate('click')

    // open the modal window
    const exportButton = wrapper.find('button.test-export-button')
    exportButton.simulate('click')
    expect(wrapper.find('div.modal-dialog')).toHaveLength(1)

    // close it
    wrapper.find('div.modal-dialog button.close').simulate('click')
    wrapper.update()
    expect(wrapper.find('div.modal-dialog')).toHaveLength(0)
  })
})
