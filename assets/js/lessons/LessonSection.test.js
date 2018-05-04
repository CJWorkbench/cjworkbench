import React from 'react'
import LessonSection from './LessonSection'
import { mount, shallow } from 'enzyme'

describe('LessonSection', () => {
  const section = {
    active: true,
    title: 'Section One',
    html: '<p>Section One HTML</p>',
    steps: [
      { html: 'Step One-Ay' },
      { html: 'Step One-<strong>Bee</strong>' },
    ],
  }

  it('renders a title', () => {
    const wrapper = shallow(<LessonSection {...section} />)
    expect(wrapper.find('h2').text()).toEqual('Section One')
  })

  it('renders the description HTML', () => {
    const wrapper = shallow(<LessonSection {...section} />)
    expect(wrapper.find('.description').html()).toEqual('<div class="description lesson-content--1"><p>Section One HTML</p></div>')
  })

  it('renders steps', () => {
    const wrapper = shallow(<LessonSection {...section} />)
    expect(wrapper.find('h3.instructions')).toHaveLength(1)
    expect(wrapper.find('ol.steps')).toHaveLength(1)
    expect(wrapper.find('LessonStep')).toHaveLength(2)
  })

  it('does not render a zero steps', () => {
    const wrapper = shallow(<LessonSection {...section} steps={[]} />)
    expect(wrapper.find('h3.instructions')).toHaveLength(0)
    expect(wrapper.find('ol.steps')).toHaveLength(0)
  })
})
