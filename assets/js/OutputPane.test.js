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
        lastRelevantDeltaId={1}
        isInputBecauseOutputIsError={false}
        wfModuleId={987}
        wfModuleStatus='ok'
        isPublic={false}
        isReadOnly={false}
        htmlOutput={false}
        showColumnLetter={false}
        {...extraProps}
      />
    )
  }

  it('matches snapshot', () => {
    const w = wrapper()
    expect(w).toMatchSnapshot()
  })

  it('renders a TableView', () => {
    const w = wrapper()
    expect(w.find('TableView')).toHaveLength(1)
  })

  it('does not render an iframe, normally', () => {
    const w = wrapper()
    expect(w.find(OutputIframe).prop('visible')).toBe(false)
  })

  it('renders when no module id', () => {
    const w = wrapper({ wfModuleId: null })
    expect(w).toMatchSnapshot()
    expect(w.find('TableView')).toHaveLength(1)
  })

  it('renders an iframe when htmlOutput', () => {
    const w = wrapper({ htmlOutput: true })
    expect(w.find(OutputIframe).prop('visible')).toBe(true)
  })
})
