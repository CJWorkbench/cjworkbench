/* globals describe, expect, it, jest */
import React from 'react'
import { WorkflowMetadata } from './WorkflowMetadata'
import { mountWithI18n } from '../i18n/test-utils'

describe('WorkflowMetadata', () => {
  const today = new Date('Fri Sep 22 2017 17:03:52 GMT-0400 (EDT)')
  const dayBefore = today.setDate(today.getDate() - 2)

  const defaultWorkflow = {
    id: 100,
    public: false,
    owner_name: 'Harry Harrison',
    last_update: dayBefore,
    read_only: false
  }

  const wrapper = (extraProps = {}, workflowExtraProps = {}) => {
    const workflow = { ...defaultWorkflow, ...workflowExtraProps }
    return mountWithI18n(
      <WorkflowMetadata
        workflow={workflow}
        test_now={today}
        openShareModal={jest.fn()}
        {...extraProps}
      />
    )
  }

  it('renders private workflow correctly', () => {
    expect(wrapper({}, { public: false })).toMatchSnapshot()
  })

  it('shows "public" when public', () => {
    const w1 = wrapper({}, { public: true })
    expect(w1.text()).toMatch(/public/)
  })

  it('shows "private" when private', () => {
    const w1 = wrapper({}, { public: false })
    expect(w1.text()).toMatch(/private/)
  })

  it('opens share modal', () => {
    const w = wrapper()
    w.find('button.public-private').simulate('click', { preventDefault: jest.fn(), stopPropagation: jest.fn() })
    expect(w.instance().props.openShareModal).toHaveBeenCalled()
  })
})
