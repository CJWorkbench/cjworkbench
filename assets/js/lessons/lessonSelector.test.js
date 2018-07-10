/* globals afterEach, beforeEach, describe, expect, it, jest */
import lessonSelector from './lessonSelector'
import update from 'immutability-helper'

describe('lessonSelector', () => {
  const initialState = {
    lessonData: {
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
            { html: 'Step One-Ay', highlight: [ { type: 'EditableNotes' } ], testJs: 'return false' },
            { html: 'Step One-<strong>Bee</strong>', highlight: [ { type: 'WfModule', moduleName: 'Foo' } ], testJs: 'return false' }
          ]
        },
        {
          title: 'Section Two',
          html: '<p>Section Two HTML</p>',
          steps: [
            { html: 'Step Two-Ay', highlight: [ { type: 'EditableNotes' } ], testJs: 'return false' },
            { html: 'Step Two-<strong>Bee</strong>', highlight: [ { type: 'WfModule', moduleName: 'Foo' } ], testJs: 'return false' }
          ]
        },
        {
          title: 'Last Section',
          html: '<p>Section Three HTML</p>',
          steps: [
            { html: 'Step Three-Ay', highlight: [ { type: 'EditableNotes' } ], testJs: 'return false' },
            { html: 'Step Three-<strong>Bee</strong>', highlight: [ { type: 'WfModule', moduleName: 'Foo' } ], testJs: 'return false' }
          ]
        }
      ]
    },
    workflow: {
    }
  }

  it('should give null values if there is no lesson', () => {
    const state = update(initialState, { $unset: [ 'lessonData' ] })
    const { activeSectionIndex, activeStepIndex, testHighlight } = lessonSelector(state)
    expect(activeSectionIndex).toBe(null)
    expect(activeStepIndex).toBe(null)
    // components will still call testHighlight(), so make it return null
    expect(testHighlight({ type: 'ModuleSearch' })).toBe(false)
  })

  it('should start with 0 indexes', () => {
    const { activeSectionIndex, activeStepIndex } = lessonSelector(initialState)
    expect(activeSectionIndex).toBe(0)
    expect(activeStepIndex).toBe(0)
  })

  it('should highlight the active index', () => {
    const state = update(initialState, { lessonData: { sections: { 0: { steps: { 0: { $merge: { highlight: [ { type: 'ModuleSearch' } ] } } } } } } })
    const { testHighlight } = lessonSelector(state)
    expect(testHighlight({ type: 'EditableNotes' })).toBe(false)
    expect(testHighlight({ type: 'ModuleSearch' })).toBe(true)
  })

  it('should find activeSectionIndex', () => {
    const state = update(initialState, { lessonData: { sections: { 0: { steps: {
      0: { $merge: { testJs: 'return true' } },
      1: { $merge: { testJs: 'return true' } }
    } } } } })
    const { activeSectionIndex, activeStepIndex } = lessonSelector(state)
    expect(activeSectionIndex).toBe(1)
    expect(activeStepIndex).toBe(0)
  })

  it('should find activeStepIndex', () => {
    const state = update(initialState, { lessonData: { sections: { 0: { steps: {
      0: { $merge: { testJs: 'return true' } }
    } } } } })
    const { activeSectionIndex, activeStepIndex } = lessonSelector(state)
    expect(activeSectionIndex).toBe(0)
    expect(activeStepIndex).toBe(1)
  })

  it('should set nulls when all steps are complete', () => {
    const state = update(initialState, { lessonData: { sections: {
      0: { steps: {
        0: { $merge: { testJs: 'return true' } },
        1: { $merge: { testJs: 'return true' } }
      } },
      1: { steps: {
        0: { $merge: { testJs: 'return true' } },
        1: { $merge: { testJs: 'return true' } }
      } },
      2: { steps: {
        0: { $merge: { testJs: 'return true' } },
        1: { $merge: { testJs: 'return true' } }
      } }
    } } })
    const { activeSectionIndex, activeStepIndex } = lessonSelector(state)
    expect(activeSectionIndex).toBe(null)
    expect(activeStepIndex).toBe(null)
  })

  it('should pass testJs `workflow`, a WorkflowWithHelpers', () => {
    const state = update(initialState, {
      lessonData: { sections: {
        0: { steps: {
          0: { $merge: { testJs: 'return workflow.wfModuleNames[0] === "foo"' } },
          1: { $merge: { testJs: 'return workflow.wfModuleNames[1] === "foo"' } }
        } }
      } },
      workflow: { $set: {
        wf_modules: [
          { module_version: { module: { name: 'foo' } } }
        ]
      } }
    })
    expect(lessonSelector(state).activeStepIndex).toBe(1)
  })

  it('should pass testJs `state`, a StateWithHelpers', () => {
    const state = update(initialState, {
      lessonData: { sections: {
        0: { steps: {
          0: { $merge: { testJs: 'return state.selectedWfModule.moduleName === "foo"' } }
        } }
      } },
      workflow: { $set: {
        wf_modules: [
          { id: 1, module_version: { module: { name: 'foo' } } }
        ]
      } },
      selected_wf_module: { $set: 0 }
    })
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
      const state = update(initialState, {
        lessonData: { sections: {
          0: { steps: {
            0: { $merge: { testJs: 'return state.selectedWfModule.moduleName === "foo"' } }
          } }
        } },
        workflow: { $set: {
          wf_modules: [
            { id: 1, module_version: { module: { name: 'foo' } } }
          ]
        } },
        selected_wf_module: { $set: null } // makes selectedWfModule null
      })
      expect(lessonSelector(state).activeStepIndex).toBe(0)
      expect(console.error).toHaveBeenCalled()
      expect(console.error.mock.calls[0][0]).toBeInstanceOf(Error)
    })
  })
})
