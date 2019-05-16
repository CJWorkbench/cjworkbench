import React from 'react'
import { mount } from 'enzyme'
import Button from './Button'

describe('Button', () => {
  const wrapper = (extraProps={}) => mount(
    <Button
      tabSlug='tab-1'
      index={2}
      className='module-search-in-between'
      isLessonHighlight={false}
      isLastAddButton={false}
      {...extraProps}
    />
  )

  it('should have .lesson-highlight', () => {
    const w = wrapper({ isLessonHighlight: true })
    expect(w.find('button.search.lesson-highlight')).toHaveLength(1)
  })
})
