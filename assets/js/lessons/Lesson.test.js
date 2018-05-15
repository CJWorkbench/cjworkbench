import React from 'react'
import { Lesson } from './Lesson'
import LessonSection from './LessonSection'
import { mount, shallow } from 'enzyme'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'

describe('Lesson', () => {
  const lesson = {
    slug: 'a-lesson',
    header: {
      title: 'Lesson Title',
      html: '<p>Lesson HTML</p>',
    },
    sections: [
      {
        title: 'Section One',
        html: '<p>Section One HTML</p>',
        steps: [
          { html: 'Step One-Ay' },
          { html: 'Step One-<strong>Bee</strong>' },
        ],
      },
      {
        title: 'Section Two',
        html: '<p>Section Two HTML</p>',
        steps: [
          { html: 'Step Two-Ay' },
          { html: 'Step Two-<strong>Bee</strong>' },
        ],
      },
      {
        title: 'Last Section',
        html: '<p>Section Three HTML</p>',
        steps: [
          { html: 'Step Three-Ay' },
          { html: 'Step Three-<strong>Bee</strong>' },
        ],
      },
    ],
  }

  const navProps = {
    activeSectionIndex: 0,
    activeStepIndex: 0,
  }

  function wrapper(extraProps) {
    return shallow(
      <Lesson {...lesson} {...navProps} {...(extraProps || {})} />
    )
  }

  describe('shallow', () => {

    it('renders a title', () => {
      expect(wrapper().find('h1').text()).toEqual('Lesson Title')
    })

    it('renders the description HTML', () => {
      expect(wrapper().find('.description').html()).toEqual('<div class="description"><p>Lesson HTML</p></div>')
    })

    it('renders LessonSections', () => {
      expect(wrapper().find(LessonSection)).toHaveLength(3)
    })

    it('sets LessonNav activeSectionIndex', () => {
      const w = wrapper({ activeSectionIndex: 1 })
      const nav = w.find('LessonNav')
    })

    it('sets LessonSection activeSectionIndex and activeStepIndex', () => {
      const w1 = wrapper({ activeSectionIndex: 1, activeStepIndex: 2 })
      expect(w1.find(LessonSection).map(s => s.prop('activeSectionIndex'))).toEqual([ 1, 1, 1 ])
      expect(w1.find(LessonSection).map(s => s.prop('activeStepIndex'))).toEqual([ 2, 2, 2 ])
    })

    it('defaults to currentSectionIndex=0', () => {
      expect(wrapper().find('LessonNav').prop('currentSectionIndex')).toBe(0)
    })
  })

  describe('navigation', () => {
    // integration-test-y: this tests that Lesson and LessonNav play nice
    function wrapper(extraProps) {
      return mount(
        <Lesson {...lesson} {...navProps} {...(extraProps || {})} />
      )
    }

    it('shows "Next" and an unclickable "Previous"', () => {
      const w = wrapper()
      expect(w.find('footer button[name="Previous"][disabled=true]')).toHaveLength(1)
      expect(w.find('footer .current-and-total').text()).toEqual('1 of 3')
      expect(w.find('section').map(n => n.prop('className'))).toEqual([ 'current', 'not-current', 'not-current' ])
      expect(w.find('footer button[name="Next"][disabled=true]')).toHaveLength(0)
    })

    it('moves to the next section', () => {
      const w = wrapper()
      w.find('footer button[name="Next"]').simulate('click')
      expect(w.find('footer button[name="Previous"][disabled=true]')).toHaveLength(0)
      expect(w.find('footer .current-and-total').text()).toEqual('2 of 3')
      expect(w.find('section').map(n => n.prop('className'))).toEqual([ 'not-current', 'current', 'not-current' ])
      expect(w.find('footer button[name="Next"][disabled=true]')).toHaveLength(0)
    })

    it('disables Next on the final section', () => {
      const w = wrapper()
      w.find('footer button[name="Next"]').simulate('click').simulate('click')
      expect(w.find('footer button[name="Previous"][disabled=true]')).toHaveLength(0)
      expect(w.find('footer .current-and-total').text()).toEqual('3 of 3')
      expect(w.find('section').map(n => n.prop('className'))).toEqual([ 'not-current', 'not-current', 'current' ])
      expect(w.find('footer button[name="Next"][disabled=true]')).toHaveLength(1)
    })
  })
})
