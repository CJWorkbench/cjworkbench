/* globals describe, expect, it, jest */
import StepList from './StepList'
import { mountWithI18n } from '../../i18n/test-utils'

describe('StepList', () => {
  const wrapper = extraProps =>
    mountWithI18n(
      <StepList
        api={{}}
        isReadOnly={false}
        tabSlug='tab-1'
        selected_step_position={null}
        steps={[]}
        modules={{}}
        reorderStep={jest.fn()}
        deleteStep={jest.fn()}
        testLessonHighlightIndex={jest.fn(i => false)}
        paneRef={{ current: null }}
        {...extraProps}
      />
    )

  it('should render a placeholder when empty and read-only', () => {
    const w = wrapper({ steps: [], isReadOnly: true })
    expect(
      w.find('Trans[id="js.WorkflowEditor.StepList.EmptyReadOnlyStepList"]')
    ).toHaveLength(1)
  })
})
