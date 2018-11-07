/* global describe, it, expect */
import React from 'react'
import { shallow } from 'enzyme'
import { OutputPane } from './OutputPane'
import OutputIframe from './OutputIframe'

describe('OutputPane', () => {
  const wrapper = function (extraProps = {}) {
    return shallow(
      <OutputPane
        api={{}}
        workflowId={123}
        wfModule={{id: 987, deltaId: 1, status: 'ok', htmlOutput: false}}
        isPublic={false}
        isReadOnly={false}
        showColumnLetter={false}
        {...extraProps}
      />
    )
  }

  it('matches snapshot', () => {
    const w = wrapper()
    expect(w).toMatchSnapshot()
  })

  it('renders a TableSwitcher', () => {
    const w = wrapper()
    expect(w.find('TableSwitcher')).toHaveLength(1)
  })

  it('renders when no module id', () => {
    const w = wrapper({ wfModule: null })
    expect(w).toMatchSnapshot()
    expect(w.find('TableSwitcher')).toHaveLength(1)
  })

  it('renders an iframe when htmlOutput', () => {
    const w = wrapper({ wfModule: { id: 1, deltaId: 2, htmlOutput: true, status: 'ok' }})
    expect(w.find(OutputIframe).prop('visible')).toBe(true)

    // When !htmlOutput, we just set visible=false but continue to display it.
    // That's because react-data-grid would have the wrong size otherwise.
    const w2 = wrapper({ wfModule: { id: 1, deltaId: 2, htmlOutput: false, status: 'ok' }})
    expect(w2.find(OutputIframe).prop('visible')).toBe(false)
  })

  it('renders a spinner when busy', () => {
    const w = wrapper({ wfModule: { id: 1, deltaId: 2, htmlOutput: true, status: 'busy' }})
    expect(w.find('.spinner-container-transparent')).toHaveLength(1)
  })

  it('renders different table than iframe when desired', () => {
    const w = wrapper({
      // even if before-error has htmlOutput, we won't display that one
      wfModuleBeforeError: { id: 1, deltaId: 2, status: 'ok', htmlOutput: true },
      wfModule: { id: 3, deltaId: 4, status: 'error', htmlOutput: true }
    })
    expect(w.find('TableSwitcher').prop('wfModuleId')).toEqual(1)
    expect(w.find('TableSwitcher').prop('deltaId')).toEqual(2)
    expect(w.text()).toMatch(/This was the data that led to an error./)
    expect(w.find(OutputIframe).prop('wfModuleId')).toEqual(3)
    expect(w.find(OutputIframe).prop('deltaId')).toEqual(4)
  })
})
