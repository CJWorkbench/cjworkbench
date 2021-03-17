/* globals describe, it, expect, jest, beforeEach, afterEach */
import { act } from 'react-dom/test-utils'
import ConnectedStep, { Step } from './Step'
import DataVersionModal from '../DataVersionModal'
import { mockStore } from '../../test-utils'
import { shallowWithI18n, mountWithI18n } from '../../i18n/test-utils'
import deepEqual from 'fast-deep-equal'
import { createStore } from 'redux'
import { Provider } from 'react-redux'

import { generateSlug } from '../../utils'
import lessonSelector from '../../lessons/lessonSelector'
import StatusLine from './StatusLine'

jest.mock('../../utils')
jest.mock('../../lessons/lessonSelector', () => jest.fn()) // same mock in every test :( ... we'll live

describe('Step, not read-only mode', () => {
  let mockApi

  beforeEach(() => {
    mockApi = {
      createOauthAccessToken: jest.fn(),
      stepResultColumnValueCounts: jest.fn()
    }
  })

  // A mock module that looks like LoadURL
  const step = {
    id: 999,
    slug: 'step-1',
    notes: '',
    is_collapsed: false, // false because we render more, so better test
    is_busy: false,
    last_relevant_delta_id: 11,
    cached_render_result_delta_id: 11,
    output_status: 'ok',
    params: {
      url: 'http://some.URL.me',
      menu_select: 1
    },
    secrets: {},
    files: [],
    output_errors: []
  }

  function pspec (idName, type, extraProps = {}) {
    return {
      idName,
      name: '',
      type,
      multiline: false,
      placeholder: '',
      visibleIf: null,
      ...extraProps
    }
  }

  const module = {
    id_name: 'loadurl', // more or less
    name: 'Load from URL',
    icon: 'icon',
    help_url: 'http://help-url',
    param_fields: [
      pspec('url', 'string'),
      pspec('menu_select', 'menu', { items: 'Mango|Banana' })
    ]
  }

  const wrapper = (extraProps = {}) => {
    return shallowWithI18n(
      <Step
        isOwner
        isReadOnly={false}
        isAnonymous={false}
        isZenMode={false}
        isZenModeAllowed={false}
        module={module}
        workflowId={99}
        step={step}
        deleteStep={jest.fn()}
        inputStep={{ id: 123, last_relevant_delta_id: 707 }}
        isSelected
        isAfterSelected={false}
        api={mockApi}
        tabs={[]}
        currentTab='tab-1'
        index={2}
        isDragging={false}
        onDragStart={jest.fn()}
        onDragEnd={jest.fn()}
        isLessonHighlight={false}
        isLessonHighlightCollapse={false}
        isLessonHighlightNotes={false}
        fetchModuleExists={false}
        clearNotifications={jest.fn()}
        setSelectedStep={jest.fn()}
        setStepCollapsed={jest.fn()}
        setStepParams={jest.fn()}
        setStepNotes={jest.fn()}
        maybeRequestFetch={jest.fn()}
        setZenMode={jest.fn()}
        applyQuickFix={jest.fn()}
        {...extraProps}
      />
    )
  }

  it('matches snapshot', () => {
    expect(wrapper()).toMatchSnapshot()
  })

  it('has .status-busy when cached result is stale', () => {
    const busyStep = {
      ...step,
      output_status: 'ok',
      last_relevant_delta_id: 12,
      cached_render_result_delta_id: 11
    }
    const w = wrapper({ step: busyStep })
    expect(w.hasClass('status-busy')).toBe(true)
    expect(w.find('ParamsForm').prop('isStepBusy')).toBe(true)
    expect(w.find(StatusLine).prop('status')).toEqual('busy')

    w.setProps({ step: { ...busyStep, cached_render_result_delta_id: 12 } })
    expect(w.hasClass('status-busy')).toBe(false)
    expect(w.hasClass('status-ok')).toBe(true)

    expect(w.find('ParamsForm').prop('isStepBusy')).toBe(false)
    expect(w.find(StatusLine).prop('status')).toEqual('ok')
    expect(w.hasClass('status-ok')).toBe(true)
    expect(w.hasClass('status-busy')).toBe(false)
  })

  it('does not render ParamsForm when collapsed', () => {
    // https://www.pivotaltracker.com/story/show/165539156
    // If we were to render a <ParamsForm> while display:none was set, the
    // params wouldn't be able to auto-size themselves.
    const w = wrapper({ step: { ...step, is_collapsed: true } })
    expect(w.find('ParamsForm').length).toEqual(0)
  })

  it('has .status-busy overridden when step.is_busy', () => {
    const w = wrapper({ step: { ...step, output_status: 'ok', is_busy: true } })
    expect(w.hasClass('status-busy')).toBe(true)
  })

  it('renders a note', () => {
    const w = wrapper({ step: { ...step, notes: 'some notes' } })
    expect(w.find('EditableNotes').prop('value')).toEqual('some notes')
  })

  it('renders in Zen mode', () => {
    const w = wrapper({ isZenMode: true })
    expect(w.prop('className')).toMatch(/\bzen-mode\b/)
    expect(w.find('ParamsForm').prop('isZenMode')).toBe(true)
  })

  it('has an "enter zen mode" button', () => {
    const w = wrapper({ isZenModeAllowed: true, isZenMode: false })
    let checkbox = w.find('input[type="checkbox"][name="zen-mode"]')
    expect(checkbox.prop('checked')).toBe(false)
    checkbox.simulate('change', { target: { checked: true } })
    expect(w.instance().props.setZenMode).toHaveBeenCalledWith(step.id, true)
    w.setProps({ isZenMode: true })

    checkbox = w.find('input[type="checkbox"][name="zen-mode"]')
    expect(checkbox.prop('checked')).toBe(true)
    checkbox.simulate('change', { target: { checked: false } })
    expect(w.instance().props.setZenMode).toHaveBeenCalledWith(step.id, false)
  })

  it('renders notifications, opening and closing a modal', () => {
    const w = wrapper({
      fetchModuleExists: true,
      isReadOnly: false,
      isAnonymous: false
    })

    w.find('button.notifications').simulate('click')
    expect(w.instance().props.clearNotifications).toHaveBeenCalledWith(999)
    expect(w.find(DataVersionModal).length).toBe(1)

    w.find(DataVersionModal).prop('onClose')()
    w.update()
    expect(w.find(DataVersionModal).length).toBe(0)
  })

  it('hides notifications when isAnonymous', () => {
    const w = wrapper({
      fetchModuleExists: true,
      isReadOnly: false,
      isAnonymous: true
    })
    expect(w.find('button.notifications').length).toBe(0)
  })

  it('hides notifications when isReadOnly', () => {
    const w = wrapper({
      fetchModuleExists: true,
      isOwner: false,
      isReadOnly: true,
      isAnonymous: false
    })
    expect(w.find('button.notifications').length).toBe(0)
  })

  it('hides notifications when there is no fetch module', () => {
    const w = wrapper({
      fetchModuleExists: false,
      isReadOnly: false,
      isAnonymous: false
    })
    expect(w.find('button.notifications').length).toBe(0)
  })

  it('adds a note', () => {
    const w = wrapper({ step: { ...step, notes: '' } })

    expect(w.find('.step-notes.visible')).toHaveLength(0)

    w.find('button.edit-note').simulate('click')
    w.find('EditableNotes').simulate('change', {
      target: { value: 'new note' }
    })
    w.find('EditableNotes').simulate('blur')

    expect(w.instance().props.setStepNotes).toHaveBeenCalledWith(
      step.id,
      'new note'
    )
  })

  it('deletes a note', () => {
    const w = wrapper({ step: { ...step, notes: 'some notes' } })

    expect(w.find('.step-notes.visible')).toHaveLength(1)

    w.find('EditableNotes').simulate('change', { target: { value: '' } })
    w.find('EditableNotes').simulate('blur')

    expect(w.instance().props.setStepNotes).toHaveBeenCalledWith(step.id, '')
  })

  it('does not show old value during edit when editing ""', () => {
    // https://www.pivotaltracker.com/story/show/163005781
    const w = wrapper({ step: { ...step, notes: 'some notes' } })

    w.find('EditableNotes').simulate('change', { target: { value: '' } })
    expect(w.find('EditableNotes').prop('value')).toEqual('')
  })

  it('queues changes from onChange and then submits them in onSubmit', () => {
    const step = {
      id: 999,
      notes: '',
      is_collapsed: false,
      params: {
        a: 'A',
        b: 'B'
      },
      secrets: {},
      files: [],
      output_errors: []
    }
    const aModule = {
      ...module,
      param_fields: [pspec('a', 'string'), pspec('b', 'string')]
    }
    // Make setStepParams() return a thennable -- a fake promise.
    // It'll set onSetStepParamsDone, which we can call synchronously.
    // (This is white-box testing -- we assume the .then() and the sync
    // call.)
    let onSetStepParamsDone = null
    const setStepParams = jest.fn(() => ({
      then: fn => {
        onSetStepParamsDone = fn
      }
    }))
    const w = wrapper({
      step,
      module: aModule,
      setStepParams
    })

    w.find('ParamsForm').prop('onChange')({ a: 'C' })
    w.update()
    expect(w.find('ParamsForm').prop('edits')).toEqual({ a: 'C' })

    // not submitted to the server
    expect(setStepParams).not.toHaveBeenCalled()
    expect(w.prop('className')).toMatch(/\bediting\b/)

    w.find('ParamsForm').prop('onSubmit')()
    expect(setStepParams).toHaveBeenCalledWith(999, { a: 'C' })

    // a bit of a white-box test: state should be cleared ... but only
    // after a tick, so Redux can do its magic in setStepParams
    expect(w.prop('className')).toMatch(/\bediting\b/)
    expect(w.state('edits')).toEqual({ a: 'C' })
    w.setProps({ step: { ...step, params: { a: 'C' } } })
    act(onSetStepParamsDone)
    expect(w.state('edits')).toEqual({})
    expect(w.prop('className')).not.toMatch(/\bediting\b/)
  })

  it('submits a fetch event in onSubmit', () => {
    // Use case:
    // 1. User edits url field
    // 2. User clicks "submit" button
    const step = {
      id: 999,
      slug: 'step-999',
      notes: '',
      is_collapsed: false,
      params: {
        url: '',
        version_select: 'B'
      },
      secrets: {},
      files: [],
      output_errors: []
    }
    const setStepParams = jest.fn(() => ({ then: jest.fn() })) // dummy promise
    const aModule = {
      ...module,
      param_fields: [pspec('url', 'string'), pspec('version_select', 'custom')]
    }
    const w = wrapper({ step, module: aModule, setStepParams })

    w.find('ParamsForm').prop('onChange')({ url: 'http://example.org' })
    w.find('ParamsForm').prop('onSubmit')()

    expect(setStepParams).toHaveBeenCalledWith(999, {
      url: 'http://example.org'
    })
    expect(w.instance().props.maybeRequestFetch).toHaveBeenCalledWith(999)
  })

  it('overrides status to busy when a fetch is pending', () => {
    const w = wrapper({ step: { ...step, nClientRequests: 1 } })
    expect(w.find('ParamsForm').prop('isStepBusy')).toBe(true)
    expect(w.find(StatusLine).prop('status')).toEqual('busy')
    expect(w.prop('className')).toMatch(/\bstatus-busy\b/)
  })

  it('applies a quick fix', () => {
    // Scenario: user is on linechart and chose non-numeric Y axis
    mockApi.setSelectedStep = jest.fn(() => Promise.resolve(null))
    mockApi.addStep = jest.fn(() => Promise.resolve(null))
    generateSlug.mockImplementation(prefix => prefix + 'X')
    const quickFix = {
      buttonText: 'Fix it',
      action: {
        type: 'prependStep',
        moduleSlug: 'dosomething',
        partialParams: { A: 'B' }
      }
    }
    const store = mockStore(
      {
        selectedPane: {
          pane: 'tab',
          tabSlug: 'tab-11'
        },
        workflow: {
          id: 99,
          tab_slugs: ['tab-11', 'tab-12'],
          read_only: false,
          is_owner: true,
          is_anonymous: false
        },
        tabs: {
          'tab-11': { slug: 'tab-11', name: 'Tab 1', step_ids: [10, 20] },
          'tab-12': { slug: 'tab-12', name: 'Tab 2', step_ids: [] }
        },
        steps: {
          10: { id: 10, slug: 'step-10', tab_slug: 'tab-11' },
          20: { id: 20, slug: 'step-20', tab_slug: 'tab-11' }
        },
        modules: {
          loadurl: {
            name: 'Load from URL',
            id_name: 'loadurl',
            help_url: '',
            icon: 'icon',
            param_fields: []
          }
        }
      },
      mockApi
    )

    lessonSelector.mockReset()
    lessonSelector.mockReturnValue({
      testHighlight: _ => false
    })

    const w = mountWithI18n(
      <Provider store={store}>
        <ConnectedStep
          isZenMode={false}
          isZenModeAllowed={false}
          index={1}
          step={{
            id: 20,
            slug: 'step-20',
            module: 'loadurl',
            is_collapsed: false,
            output_status: 'error',
            params: {},
            secrets: {},
            output_errors: [{ message: 'foo', quickFixes: [quickFix] }],
            files: []
          }}
          isSelected
          isAfterSelected={false}
          onDragStart={jest.fn()}
          onDragEnd={jest.fn()}
          isDragging={false}
          setZenMode={jest.fn()}
          api={mockApi}
        />
      </Provider>
    )

    w.find('button.quick-fix').simulate('click')
    expect(mockApi.addStep).toHaveBeenCalledWith(
      'tab-11',
      'step-X',
      'dosomething',
      1,
      { A: 'B' }
    )
  })

  describe('lesson highlights', () => {
    let store
    let wrapper = null
    let nonce = 0

    function highlight (selectors) {
      lessonSelector.mockReturnValue({
        testHighlight: test => {
          return selectors.some(s => deepEqual(test, s))
        }
      })

      // trigger a change
      store.dispatch({ type: 'whatever', payload: ++nonce })
      if (wrapper !== null) wrapper.update()
    }

    beforeEach(() => {
      lessonSelector.mockReset()

      store = createStore((_, action) => ({
        selectedPane: {
          pane: 'tab',
          tabSlug: 'tab-11'
        },
        workflow: {
          id: 99,
          read_only: false,
          is_anonymous: false,
          is_owner: false,
          tab_slugs: ['tab-11']
        },
        tabs: {
          'tab-11': { slug: 'tab-11', name: 'Tab 1', step_ids: [1, 2, 999] }
        },
        steps: {
          999: { slug: 'step-99', module: 'loadurl', params: {}, secrets: {} }
        },
        modules: {
          loadurl: {
            id_name: 'loadurl',
            name: 'Load from URL',
            help_url: '',
            icon: 'icon',
            param_fields: [pspec('url', 'string')]
          }
        },
        ...action.payload
      }))

      highlight([])

      wrapper = mountWithI18n(
        <Provider store={store}>
          <ConnectedStep
            isZenMode={false}
            isZenModeAllowed={false}
            index={1}
            step={{
              id: 20,
              slug: 'step-20',
              module: 'loadurl',
              is_collapsed: false,
              output_status: 'error',
              params: {},
              secrets: {},
              output_errors: [{ message: 'foo', quickFixes: [] }],
              files: []
            }}
            isSelected
            isAfterSelected={false}
            onDragStart={jest.fn()}
            onDragEnd={jest.fn()}
            isDragging={false}
            setZenMode={jest.fn()}
            api={mockApi}
          />
        </Provider>
      )
    })
    afterEach(() => {
      if (wrapper !== null) {
        wrapper.unmount()
        wrapper = null
      }
    })

    it('highlights a Step', () => {
      highlight([{ type: 'Step', index: 1, moduleIdName: 'loadurl' }])
      expect(wrapper.find('.step').prop('className')).toMatch(
        /\blesson-highlight\b/
      )
    })

    it('unhighlights a Step', () => {
      // wrong name
      highlight([{ type: 'Step', index: 1, moduleIdName: 'TestModule2' }])
      expect(wrapper.find('.step').prop('className')).not.toMatch(
        /\blesson-highlight\b/
      )
    })

    it('highlights the "collapse" button', () => {
      highlight([
        {
          type: 'StepContextButton',
          index: 1,
          moduleIdName: 'loadurl',
          button: 'collapse'
        }
      ])
      expect(
        wrapper.find('i.context-collapse-button').prop('className')
      ).toMatch(/\blesson-highlight\b/)
    })

    it('unhighlights the "collapse" button', () => {
      // wrong moduleIdName
      highlight([
        {
          type: 'StepContextButton',
          index: 1,
          moduleIdName: 'TestModule2',
          button: 'collapse'
        }
      ])
      expect(
        wrapper.find('i.context-collapse-button').prop('className')
      ).not.toMatch(/\blesson-highlight\b/)

      // wrong button
      highlight([
        {
          type: 'StepContextButton',
          index: 1,
          moduleIdName: 'loadurl',
          button: 'notes'
        }
      ])
      expect(
        wrapper.find('i.context-collapse-button').prop('className')
      ).not.toMatch(/\blesson-highlight\b/)
    })

    it('highlights the notes button', () => {
      highlight([
        {
          type: 'StepContextButton',
          index: 1,
          moduleIdName: 'loadurl',
          button: 'notes'
        }
      ])
      expect(wrapper.find('button.edit-note').prop('className')).toMatch(
        /\blesson-highlight\b/
      )
    })

    it('unhighlights the notes button', () => {
      // wrong moduleName
      highlight([
        {
          type: 'StepContextButton',
          index: 1,
          moduleName: 'TestModule2',
          button: 'notes'
        }
      ])
      expect(wrapper.find('button.edit-note').prop('className')).not.toMatch(
        /\blesson-highlight\b/
      )
    })
  })
})
