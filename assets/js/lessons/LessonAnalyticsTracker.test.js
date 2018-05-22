import React from 'react'
import { shallow } from 'enzyme'
import LessonAnalyticsTracker from './LessonAnalyticsTracker'

describe('LessonAnalyticsTracker', () => {
  const lesson = {
    slug: 'a-lesson',
    sections: [
      { title: 'Section One', },
      { title: 'Section Two', },
      { title: 'Last Section', },
    ],
  }

  let send

  beforeEach(() => send = null)

  function wrapper(extraProps) {
    send = jest.fn()
    return shallow(
      <LessonAnalyticsTracker
        {...lesson}
        trackMaxProgress={send}
        activeSectionIndex={0}
        activeStepIndex={0}
        {...(extraProps || {})}
        />
    )
  }

  it('sends 0,0 on first load', () => {
    wrapper()
    expect(send).toHaveBeenCalledWith('a-lesson', 'Section One', 0)
  })

  it('sends 0,1 on increment step', () => {
    const w = wrapper()
    w.setProps({ activeStepIndex: 1 })
    expect(send).toHaveBeenCalledWith('a-lesson', 'Section One', 1)
  })

  it('does not re-send 0,0', () => {
    const w = wrapper()
    w.setProps({ activeStepIndex: 1 })
    w.setProps({ activeStepIndex: 0 })
    expect(send).toHaveBeenCalledTimes(2)
  })

  it('sends 1,0 on increment section', () => {
    const w = wrapper()
    w.setProps({ activeStepIndex: 2 })
    w.setProps({ activeSectionIndex: 1, activeStepIndex: 0 })
    expect(send).toHaveBeenCalledWith('a-lesson', 'Section Two', 0)
  })

  it('never decrements section', () => {
    const w = wrapper()
    w.setProps({ activeSectionIndex: 1, activeStepIndex: 0 })
    w.setProps({ activeSectionIndex: 0, activeStepIndex: 1 })
    expect(send).toHaveBeenCalledTimes(2)
  })

  it('sends null on done', () => {
    const w = wrapper()
    w.setProps({ activeSectionIndex: null, activeStepIndex: null })
    expect(send).toHaveBeenCalledWith('a-lesson', null, null)
  })

  it('never sends after nulls', () => {
    const w = wrapper()
    w.setProps({ activeSectionIndex: null, activeStepIndex: null })
    w.setProps({ activeSectionIndex: 1, activeStepIndex: 2 })
    expect(send).toHaveBeenCalledTimes(2)
  })
})
