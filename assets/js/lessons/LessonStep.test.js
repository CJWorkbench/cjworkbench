/* globals describe, expect, it */
import React from 'react'
import LessonStep from './LessonStep'
import { shallow } from 'enzyme'

describe('LessonStep', () => {
  const step = {
    html: '<p>This is</p><p>a <em>step</em></p>',
    status: 'done'
  }

  it('renders the description HTML', () => {
    const wrapper = shallow(<LessonStep {...step} />)
    expect(wrapper.find('.description').html()).toEqual('<div class="description"><p>This is</p><p>a <em>step</em></p></div>')
  })

  it('renders the status', () => {
    const wrapper = shallow(<LessonStep {...step} />)
    expect(wrapper.prop('className')).toMatch(/\bdone\b/)
  })
})
