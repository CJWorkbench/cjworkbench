/* globals afterEach, beforeEach, describe, expect, it, jest */
import lessonSelector from './lessonSelector'

describe('lessonSelector', () => {
  const lessonFixture = {
    slug: 'a-lesson',
    header: {
      title: 'Lesson Title',
      html: '<p>Lesson HTML</p>'
    },
    sections: [
      {
        title: 'Section One',
        html: '<p>Section One HTML</p>',
        steps: [
          { html: 'Step One-Ay', highlight: [{ type: 'EditableNotes' }], testJs: 'return false' },
          { html: 'Step One-<strong>Bee</strong>', highlight: [{ type: 'WfModule', moduleIdName: 'foo' }], testJs: 'return false' }
        ]
      },
      {
        title: 'Section Two',
        html: '<p>Section Two HTML</p>',
        steps: [
          { html: 'Step Two-Ay', highlight: [{ type: 'EditableNotes' }], testJs: 'return false' },
          { html: 'Step Two-<strong>Bee</strong>', highlight: [{ type: 'WfModule', moduleIdName: 'foo' }], testJs: 'return false' }
        ]
      },
      {
        title: 'Last Section',
        html: '<p>Section Three HTML</p>',
        steps: [
          { html: 'Step Three-Ay', highlight: [{ type: 'EditableNotes' }], testJs: 'return false' },
          { html: 'Step Three-<strong>Bee</strong>', highlight: [{ type: 'WfModule', moduleIdName: 'foo' }], testJs: 'return false' }
        ]
      }
    ]
  }

  it('should give null values if there is no lesson', () => {
    const state = { workflow: {} }
    const { activeSectionIndex, activeStepIndex, testHighlight } = lessonSelector(state)
    expect(activeSectionIndex).toBe(null)
    expect(activeStepIndex).toBe(null)
    // components will still call testHighlight(), so make it return null
    expect(testHighlight({ type: 'ModuleSearch' })).toBe(false)
  })

  it('should start with 0 indexes', () => {
    const state = {
      lessonData: lessonFixture,
      workflow: {
        tab_slugs: ['tab-1'],
        selected_tab_position: 0
      },
      tabs: {
        'tab-1': { wf_modules: [] }
      },
      wfModules: {}
    }
    const { activeSectionIndex, activeStepIndex } = lessonSelector(state)
    expect(activeSectionIndex).toBe(0)
    expect(activeStepIndex).toBe(0)
  })

  it('should highlight the active index', () => {
    const state = {
      lessonData: {
        ...lessonFixture,
        sections: [
          {
            steps: [
              {
                ...lessonFixture.sections[0].steps[0],
                highlight: [{ type: 'ModuleSearch' }]
              }
            ]
          }
        ]
      },
      workflow: {
        tab_slugs: ['tab-1'],
        selected_tab_position: 0
      },
      tabs: {
        'tab-1': { wf_module_ids: [] }
      }
    }
    const { testHighlight } = lessonSelector(state)
    expect(testHighlight({ type: 'EditableNotes' })).toBe(false)
    expect(testHighlight({ type: 'ModuleSearch' })).toBe(true)
  })

  it('should find activeSectionIndex', () => {
    const state = {
      lessonData: {
        ...lessonFixture,
        sections: [
          {
            steps: [
              {
                ...lessonFixture.sections[0].steps[0],
                testJs: 'return true'
              },
              {
                ...lessonFixture.sections[0].steps[1],
                testJs: 'return true'
              }
            ]
          },
          ...lessonFixture.sections.slice(1)
        ]
      },
      workflow: {
        tab_slugs: ['tab-1'],
        selected_tab_position: 0
      },
      tabs: {
        'tab-1': { wf_module_ids: [] }
      }
    }
    const { activeSectionIndex, activeStepIndex } = lessonSelector(state)
    expect(activeSectionIndex).toBe(1)
    expect(activeStepIndex).toBe(0)
  })

  it('should find activeStepIndex', () => {
    const state = {
      lessonData: {
        ...lessonFixture,
        sections: [
          {
            steps: [
              {
                ...lessonFixture.sections[0].steps[0],
                testJs: 'return true'
              },
              ...lessonFixture.sections[0].steps.slice(1)
            ]
          },
          ...lessonFixture.sections.slice(1)
        ]
      }
    }
    const { activeSectionIndex, activeStepIndex } = lessonSelector(state)
    expect(activeSectionIndex).toBe(0)
    expect(activeStepIndex).toBe(1)
  })

  it('should set nulls when all steps are complete', () => {
    const state = {
      lessonData: {
        ...lessonFixture,
        sections: [
          { steps: [{ testJs: 'return true' }, { testJs: 'return true' }] },
          { steps: [{ testJs: 'return true' }, { testJs: 'return true' }] }
        ]
      }
    }
    const { activeSectionIndex, activeStepIndex } = lessonSelector(state)
    expect(activeSectionIndex).toBe(null)
    expect(activeStepIndex).toBe(null)
  })

  it('should pass testJs `workflow`, a WorkflowWithHelpers', () => {
    const state = {
      lessonData: {
        ...lessonFixture,
        sections: [
          {
            steps: [
              { testJs: 'return workflow.selectedTab.wfModuleSlugs[0] === "foo"' },
              { testJs: 'return workflow.selectedTab.wfModuleSlugs[1] === "foo"' }
            ]
          },
          ...lessonFixture.sections.slice(1)
        ]
      },
      workflow: {
        tab_slugs: ['tab-1', 'tab-2'],
        selected_tab_position: 0
      },
      tabs: {
        'tab-1': { wf_module_ids: [3, 4] },
        'tab-2': { wf_module_ids: [] }
      },
      wfModules: {
        3: { module: 'foo' },
        4: { module: 'bar' }
      },
      modules: {
        foo: { name: 'Foo' },
        bar: { name: 'Bar' }
      }
    }
    expect(lessonSelector(state).activeStepIndex).toBe(1)
  })

  it('should pass testJs `state`, a StateWithHelpers', () => {
    const state = {
      lessonData: {
        ...lessonFixture,
        sections: [
          {
            steps: [
              { testJs: 'return state.selectedTab.wfModuleSlugs[0] === "foo"' },
              { testJs: 'return state.selectedTab.wfModuleSlugs[1] === "foo"' }
            ]
          },
          ...lessonFixture.sections.slice(1)
        ]
      },
      workflow: {
        tab_slugs: ['tab-1', 'tab-2'],
        selected_tab_position: 0
      },
      tabs: {
        'tab-1': { wf_module_ids: [3, 4], selected_wf_module_position: 1 },
        'tab-2': { wf_module_ids: [] }
      },
      wfModules: {
        3: { module: 'foo' },
        4: { module: 'bar' }
      },
      modules: {
        foo: { name: 'Foo' },
        bar: { name: 'Bar' }
      }
    }
    expect(lessonSelector(state).activeStepIndex).toBe(1)
  })

  describe('with mocked logging', () => {
    let globalConsole
    beforeEach(() => {
      globalConsole = global.console
      global.console = { error: jest.fn() }
    })
    afterEach(() => {
      global.console = globalConsole
    })

    it('should log error on JS error', () => {
      const state = {
        lessonData: {
          sections: [
            {
              steps: [
                { testJs: 'return state.selectedWfModule.moduleSlug === "foo"' }
              ]
            }
          ]
        },
        workflow: {
          tab_slugs: ['tab-1'],
          selected_tab_position: 0
        },
        tabs: {
          'tab-1': { wf_module_ids: [], selected_wf_module_position: null }
        }
      }
      expect(lessonSelector(state).activeStepIndex).toBe(0)
      expect(console.error).toHaveBeenCalled()
      expect(console.error.mock.calls[0][0]).toBeInstanceOf(Error)
    })
  })
})
