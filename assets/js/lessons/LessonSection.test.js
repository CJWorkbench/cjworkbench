import React from 'react'
import ConnectedLessionSection, { LessonSection } from './LessonSection'
import { mount, shallow } from 'enzyme'

describe('LessonSection', () => {

  let commonProps
  beforeEach(() => {
    commonProps = {
      active: true,
      title: 'Section One',
      html: '<p>Section One HTML</p>',
      steps: [
        { html: 'Step One-Ay', highlight: [{"type":"EditableNotes"}], testJs: 'return true' },
        { html: 'Step One-<strong>Bee</strong>', highlight: [{"type":"ModuleSearch"}], testJs: 'return false' },
      ],
      setLessonHighlight: jest.fn(),
      activeStepIndex: 1,
    }
  })

  it('renders a title', () => {
    const wrapper = shallow(<LessonSection {...commonProps} />)
    expect(wrapper.find('h2').text()).toEqual('Section One')
  })

  it('renders the description HTML', () => {
    const wrapper = shallow(<LessonSection {...commonProps} />)
    expect(wrapper.find('.description').html()).toEqual('<div class="description lesson-content--1"><p>Section One HTML</p></div>')
  })

  it('renders steps', () => {
    const wrapper = shallow(<LessonSection {...commonProps} />)
    expect(wrapper.find('h3.instructions')).toHaveLength(1)
    expect(wrapper.find('ol.steps')).toHaveLength(1)
    expect(wrapper.find('LessonStep')).toHaveLength(2)
  })

  it('does not render a zero steps', () => {
    const wrapper = shallow(<LessonSection {...commonProps} steps={[]} />)
    expect(wrapper.find('h3.instructions')).toHaveLength(0)
    expect(wrapper.find('ol.steps')).toHaveLength(0)
  })

  it('runs setLessonHighlight when active', () => {
    const wrapper = shallow(<LessonSection {...commonProps} active={true} activeStepIndex={1} />)
    expect(commonProps.setLessonHighlight).toHaveBeenCalledWith([{"type":"ModuleSearch"}])
  })

  it('runs setLessonHighlight([]) when active without active steps', () => {
    const wrapper = shallow(<LessonSection {...commonProps} active={true} activeStepIndex={null} />)
    expect(commonProps.setLessonHighlight).toHaveBeenCalledWith([])
  })

  it('does not run setLessonHighlight when inactive', () => {
    const wrapper = shallow(<LessonSection {...commonProps} active={false} />)
    expect(commonProps.setLessonHighlight).not.toHaveBeenCalled()
  })
})
