/* globals describe, expect, it */
import { mountWithI18n } from '../../i18n/test-utils'
import Button from './Button'

describe('Button', () => {
  const wrapper = (extraProps = {}) => mountWithI18n(
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
