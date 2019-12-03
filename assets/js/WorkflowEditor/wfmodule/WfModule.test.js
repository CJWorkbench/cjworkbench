/* globals describe, it, expect, jest, beforeEach, afterEach */
import React from 'react'
import { act } from 'react-dom/test-utils'
import ConnectedWfModule, { WfModule } from './WfModule'
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

describe('WfModule, not read-only mode', () => {
  let mockApi

  beforeEach(() => {
    mockApi = {
      createOauthAccessToken: jest.fn(),
      valueCounts: jest.fn()
    }
  })

  // A mock module that looks like LoadURL
  const wfModule = {
    id: 999,
    slug: 'step-1',
    notes: '',
    is_collapsed: false, // false because we render more, so better test
    is_busy: false,
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
      <WfModule
        isReadOnly={false}
        isAnonymous={false}
        isZenMode={false}
        isZenModeAllowed={false}
        module={module}
        workflowId={99}
        wfModule={wfModule}
        removeModule={jest.fn()}
        inputWfModule={{ id: 123, last_relevant_delta_id: 707 }}
        isSelected
        isAfterSelected={false}
        api={mockApi}
        tabs={[]}
        currentTab='tab-1'
        index={2}
        onDragStart={jest.fn()}
        onDragEnd={jest.fn()}
        isLessonHighlight={false}
        isLessonHighlightCollapse={false}
        isLessonHighlightNotes={false}
        fetchModuleExists={false}
        clearNotifications={jest.fn()}
        setSelectedWfModule={jest.fn()}
        setWfModuleCollapsed={jest.fn()}
        setWfModuleParams={jest.fn()}
        setWfModuleNotes={jest.fn()}
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

  it('is has .status-busy', () => {
    const w = wrapper({ wfModule: { ...wfModule, output_status: 'busy' } })
    expect(w.hasClass('status-busy')).toBe(true)
    expect(w.find('ParamsForm').prop('isWfModuleBusy')).toBe(true)
    expect(w.find(StatusLine).prop('status')).toEqual('busy')

    w.setProps({ wfModule: { ...wfModule, output_status: 'ok' } })
    w.update()
    expect(w.hasClass('status-busy')).toBe(false)
    expect(w.hasClass('status-ok')).toBe(true)

    expect(w.find('ParamsForm').prop('isWfModuleBusy')).toBe(false)
    expect(w.find(StatusLine).prop('status')).toEqual('ok')
    expect(w.hasClass('status-ok')).toBe(true)
    expect(w.hasClass('status-busy')).toBe(false)
  })

  it('does not render ParamsForm when collapsed', () => {
    // https://www.pivotaltracker.com/story/show/165539156
    // If we were to render a <ParamsForm> while display:none was set, the
    // params wouldn't be able to auto-size themselves.
    const w = wrapper({ wfModule: { ...wfModule, is_collapsed: true } })
    expect(w.find('ParamsForm').length).toEqual(0)
  })

  it('has .status-busy overridden when wfModule.is_busy', () => {
    const w = wrapper({ wfModule: { ...wfModule, output_status: 'ok', is_busy: true } })
    expect(w.hasClass('status-busy')).toBe(true)
  })

  it('renders a note', () => {
    const w = wrapper({ wfModule: { ...wfModule, notes: 'some notes' } })
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
    expect(w.instance().props.setZenMode).toHaveBeenCalledWith(wfModule.id, true)
    w.setProps({ isZenMode: true })

    checkbox = w.find('input[type="checkbox"][name="zen-mode"]')
    expect(checkbox.prop('checked')).toBe(true)
    checkbox.simulate('change', { target: { checked: false } })
    expect(w.instance().props.setZenMode).toHaveBeenCalledWith(wfModule.id, false)
  })

  it('renders notifications, opening and closing a modal', () => {
    const w = wrapper({ fetchModuleExists: true, isReadOnly: false, isAnonymous: false })

    w.find('button.notifications').simulate('click')
    expect(w.instance().props.clearNotifications).toHaveBeenCalledWith(999)
    expect(w.find(DataVersionModal).length).toBe(1)

    w.find(DataVersionModal).prop('onClose')()
    w.update()
    expect(w.find(DataVersionModal).length).toBe(0)
  })

  it('hides notifications when isAnonymous', () => {
    const w = wrapper({ fetchModuleExists: true, isReadOnly: false, isAnonymous: true })
    expect(w.find('button.notifications').length).toBe(0)
  })

  it('hides notifications when isReadOnly', () => {
    const w = wrapper({ fetchModuleExists: true, isReadOnly: true, isAnonymous: false })
    expect(w.find('button.notifications').length).toBe(0)
  })

  it('hides notifications when there is no fetch module', () => {
    const w = wrapper({ fetchModuleExists: false, isReadOnly: false, isAnonymous: false })
    expect(w.find('button.notifications').length).toBe(0)
  })

  it('adds a note', () => {
    const w = wrapper({ wfModule: { ...wfModule, notes: '' } })

    expect(w.find('.module-notes.visible')).toHaveLength(0)

    w.find('button.edit-note').simulate('click')
    w.find('EditableNotes').simulate('change', { target: { value: 'new note' } })
    w.find('EditableNotes').simulate('blur')

    expect(w.instance().props.setWfModuleNotes).toHaveBeenCalledWith(wfModule.id, 'new note')
  })

  it('deletes a note', () => {
    const w = wrapper({ wfModule: { ...wfModule, notes: 'some notes' } })

    expect(w.find('.module-notes.visible')).toHaveLength(1)

    w.find('EditableNotes').simulate('change', { target: { value: '' } })
    w.find('EditableNotes').simulate('blur')

    expect(w.instance().props.setWfModuleNotes).toHaveBeenCalledWith(wfModule.id, '')
  })

  it('does not show old value during edit when editing ""', () => {
    // https://www.pivotaltracker.com/story/show/163005781
    const w = wrapper({ wfModule: { ...wfModule, notes: 'some notes' } })

    w.find('EditableNotes').simulate('change', { target: { value: '' } })
    expect(w.find('EditableNotes').prop('value')).toEqual('')
  })

  it('queues changes from onChange and then submits them in onSubmit', () => {
    const wfModule = {
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
    // Make setWfModuleParams() return a thennable -- a fake promise.
    // It'll set onSetWfModuleParamsDone, which we can call synchronously.
    // (This is white-box testing -- we assume the .then() and the sync
    // call.)
    let onSetWfModuleParamsDone = null
    const setWfModuleParams = jest.fn(() => ({ then: (fn) => { onSetWfModuleParamsDone = fn } }))
    const w = wrapper({
      wfModule,
      module: aModule,
      setWfModuleParams
    })

    w.find('ParamsForm').prop('onChange')({ a: 'C' })
    w.update()
    expect(w.find('ParamsForm').prop('edits')).toEqual({ a: 'C' })

    // not submitted to the server
    expect(setWfModuleParams).not.toHaveBeenCalled()
    expect(w.prop('className')).toMatch(/\bediting\b/)

    w.find('ParamsForm').prop('onSubmit')()
    expect(setWfModuleParams).toHaveBeenCalledWith(999, { a: 'C' })

    // a bit of a white-box test: state should be cleared ... but only
    // after a tick, so Redux can do its magic in setWfModuleParams
    expect(w.prop('className')).toMatch(/\bediting\b/)
    expect(w.state('edits')).toEqual({ a: 'C' })
    w.setProps({ wfModule: { ...wfModule, params: { a: 'C' } } })
    act(onSetWfModuleParamsDone)
    expect(w.state('edits')).toEqual({})
    expect(w.prop('className')).not.toMatch(/\bediting\b/)
  })

  it('submits a fetch event in onSubmit', () => {
    // Use case:
    // 1. User edits url field
    // 2. User clicks "submit" button
    const wfModule = {
      id: 999,
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
    const setWfModuleParams = jest.fn(() => ({ then: jest.fn() })) // dummy promise
    const aModule = {
      ...module,
      param_fields: [pspec('url', 'string'), pspec('version_select', 'custom')]
    }
    const w = wrapper({ wfModule, module: aModule, setWfModuleParams })

    w.find('ParamsForm').prop('onChange')({ url: 'http://example.org' })
    w.find('ParamsForm').prop('onSubmit')()

    expect(setWfModuleParams).toHaveBeenCalledWith(999, { url: 'http://example.org' })
    expect(w.instance().props.maybeRequestFetch).toHaveBeenCalledWith(999)
  })

  it('overrides status to busy when a fetch is pending', () => {
    const w = wrapper({ wfModule: { ...wfModule, nClientRequests: 1 } })
    expect(w.find('ParamsForm').prop('isWfModuleBusy')).toBe(true)
    expect(w.find(StatusLine).prop('status')).toEqual('busy')
    expect(w.prop('className')).toMatch(/\bstatus-busy\b/)
  })

  it('applies a quick fix', () => {
    // Scenario: user is on linechart and chose non-numeric Y axis
    mockApi.setSelectedWfModule = jest.fn(() => Promise.resolve(null))
    mockApi.addModule = jest.fn(() => Promise.resolve(null))
    generateSlug.mockImplementation(prefix => prefix + 'X')
    const quickFix = {
      buttonText: 'Fix it',
      action: { type: 'prependStep', moduleSlug: 'dosomething', partialParams: { A: 'B' } }
    }
    const store = mockStore({
      workflow: {
        id: 99,
        tab_slugs: ['tab-11', 'tab-12'],
        read_only: false,
        is_anonymous: false,
        selected_tab_position: 0
      },
      tabs: {
        'tab-11': { slug: 'tab-11', name: 'Tab 1', wf_module_ids: [10, 20] },
        'tab-12': { slug: 'tab-12', name: 'Tab 2', wf_module_ids: [] }
      },
      wfModules: {
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
    }, mockApi)

    lessonSelector.mockReset()
    lessonSelector.mockReturnValue({
      testHighlight: _ => false
    })

    const w = mountWithI18n(
      <Provider store={store}>
        <ConnectedWfModule
          isReadOnly={false}
          isAnonymous={false}
          isZenMode={false}
          isZenModeAllowed={false}
          index={1}
          wfModule={{ id: 20, module: 'loadurl', is_collapsed: false, status: 'error', params: {}, secrets: {}, output_errors: [{ message: 'foo', quickFixes: [quickFix] }], files: [] }}
          isSelected
          isAfterSelected={false}
          onDragStart={jest.fn()}
          onDragEnd={jest.fn()}
          setZenMode={jest.fn()}
          api={mockApi}
        />
      </Provider>
    )

    w.find('button.quick-fix').simulate('click')
    expect(mockApi.addModule).toHaveBeenCalledWith('tab-11', 'step-X', 'dosomething', 1, { A: 'B' })
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
        workflow: {
          id: 99,
          read_only: false,
          is_anonymous: false,
          tab_slugs: ['tab-11'],
          selected_tab_position: 0
        },
        tabs: {
          'tab-11': { slug: 'tab-11', name: 'Tab 1', wf_module_ids: [1, 2, 999] }
        },
        wfModules: {
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
          <ConnectedWfModule
            isReadOnly={false}
            isAnonymous={false}
            isZenMode={false}
            isZenModeAllowed={false}
            index={1}
            wfModule={{ id: 20, module: 'loadurl', is_collapsed: false, status: 'error', params: {}, secrets: {}, output_errors: [{ message: 'foo', quickFixes: [] }], files: [] }}
            isSelected
            isAfterSelected={false}
            onDragStart={jest.fn()}
            onDragEnd={jest.fn()}
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

    it('highlights a WfModule', () => {
      highlight([{ type: 'WfModule', index: 1, moduleName: 'Load from URL' }])
      expect(wrapper.find('.wf-module').prop('className')).toMatch(/\blesson-highlight\b/)
    })

    it('unhighlights a WfModule', () => {
      // wrong name
      highlight([{ type: 'WfModule', index: 1, moduleName: 'TestModule2' }])
      expect(wrapper.find('.wf-module').prop('className')).not.toMatch(/\blesson-highlight\b/)
    })

    it('highlights the "collapse" button', () => {
      highlight([{ type: 'WfModuleContextButton', index: 1, moduleName: 'Load from URL', button: 'collapse' }])
      expect(wrapper.find('i.context-collapse-button').prop('className')).toMatch(/\blesson-highlight\b/)
    })

    it('unhighlights the "collapse" button', () => {
      // wrong moduleName
      highlight([{ type: 'WfModuleContextButton', index: 1, moduleName: 'TestModule2', button: 'collapse' }])
      expect(wrapper.find('i.context-collapse-button').prop('className')).not.toMatch(/\blesson-highlight\b/)

      // wrong button
      highlight([{ type: 'WfModuleContextButton', index: 1, moduleName: 'Load from URL', button: 'notes' }])
      expect(wrapper.find('i.context-collapse-button').prop('className')).not.toMatch(/\blesson-highlight\b/)
    })

    it('highlights the notes button', () => {
      highlight([{ type: 'WfModuleContextButton', index: 1, moduleName: 'Load from URL', button: 'notes' }])
      expect(wrapper.find('button.edit-note').prop('className')).toMatch(/\blesson-highlight\b/)
    })

    it('unhighlights the notes button', () => {
      // wrong moduleName
      highlight([{ type: 'WfModuleContextButton', index: 1, moduleName: 'TestModule2', button: 'notes' }])
      expect(wrapper.find('button.edit-note').prop('className')).not.toMatch(/\blesson-highlight\b/)
    })
  })
})
