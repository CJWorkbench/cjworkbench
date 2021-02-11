/* globals describe, expect, it, jest */
import LessonSection from './LessonSection'
import { shallow } from 'enzyme'

describe('LessonSection', () => {
  const commonProps = {
    active: true,
    title: 'Section One',
    html: '<p>Section One HTML</p>',
    steps: [
      { html: 'Step One-Ay' },
      { html: 'Step One-<strong>Bee</strong>' },
      { html: 'Step One-<strong>See?</strong>' }
    ],
    setLessonHighlight: jest.fn(),
    index: 1,
    isCurrent: true,
    activeStepIndex: 2,
    activeSectionIndex: 1
  }

  function wrapper (extraProps) {
    return shallow(<LessonSection {...commonProps} {...(extraProps || {})} />)
  }

  it('renders a title', () => {
    expect(wrapper().find('h2').text()).toEqual('Section One')
  })

  it('renders .not-current when !isCurrent', () => {
    expect(wrapper({ isCurrent: false }).prop('className')).toMatch(/\bnot-current\b/)
  })

  it('renders the description HTML', () => {
    expect(wrapper().find('.description').html()).toEqual('<div class="description"><p>Section One HTML</p></div>')
  })

  it('renders steps', () => {
    const w = wrapper()
    expect(w.find('ol.steps')).toHaveLength(1)
    expect(w.find('LessonStep')).toHaveLength(3)
  })

  it('renders steps as FUTURE when index<activeStepIndex', () => {
    const w = wrapper({ index: 1, activeSectionIndex: 0, activeStepIndex: 1 })
    expect(w.find('LessonStep').map(s => s.prop('status'))).toEqual(['future', 'future', 'future'])
  })

  it('renders steps as DONE when index>activeStepIndex', () => {
    const w = wrapper({ index: 1, activeSectionIndex: 2, activeStepIndex: 1 })
    expect(w.find('LessonStep').map(s => s.prop('status'))).toEqual(['done', 'done', 'done'])
  })

  it('renders steps as FUTURE, ACTIVE and DONE when index==activeStepIndex', () => {
    const w = wrapper({ index: 1, activeSectionIndex: 1, activeStepIndex: 1 })
    expect(w.find('LessonStep').map(s => s.prop('status'))).toEqual(['done', 'active', 'future'])
  })

  it('renders steps as DONE when activeSectionIndex === null', () => {
    const w = wrapper({ index: 1, activeSectionIndex: null, activeStepIndex: null })
    expect(w.find('LessonStep').map(s => s.prop('status'))).toEqual(['done', 'done', 'done'])
  })

  it('does not render zero steps', () => {
    const w = wrapper({ steps: [] })
    expect(w.find('h3.instructions')).toHaveLength(0)
    expect(w.find('ol.steps')).toHaveLength(0)
  })
})
