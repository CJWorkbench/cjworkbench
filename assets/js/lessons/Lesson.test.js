import React from 'react'
import Lesson from './Lesson'
import { mount, shallow } from 'enzyme'

describe('Lesson', () => {
  const lesson = {
    stub: 'a-lesson',
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
    ],
  }

  it('renders a title', () => {
    const wrapper = shallow(<Lesson {...lesson} />)
    expect(wrapper.find('h1').text()).toEqual('Lesson Title')
  })

  it('renders the description HTML', () => {
    const wrapper = shallow(<Lesson {...lesson} />)
    expect(wrapper.find('.description').html()).toEqual('<div class="description"><p>Lesson HTML</p></div>')
  })

  it('renders LessonSections', () => {
    const wrapper = shallow(<Lesson {...lesson} />)
    expect(wrapper.find('LessonSection')).toHaveLength(2)
  })
})
