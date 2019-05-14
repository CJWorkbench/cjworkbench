import React from 'react'
import { ModuleStack } from './ModuleStack'
import { mount } from 'enzyme'

describe('ModuleStack', () => {
  const wrapper = (extraProps) => mount(
    <ModuleStack
      api={{}}
      isReadOnly={false}
      tabSlug='tab-1'
      selected_wf_module_position={null}
      wfModules={[]}
      moveModuleByIndex={jest.fn()}
      removeModule={jest.fn()}
      testLessonHighlightIndex={jest.fn((i) => false)}
      {...extraProps}
    />
  )

  it('should render a placeholder when empty and read-only', () => {
    const w = wrapper({ wfModules: [], isReadOnly: true })
    expect(w.text()).toMatch(/This Tab has no Steps./)
  })
})
