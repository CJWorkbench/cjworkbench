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
        wfModule={{id: 987, lastRelevantDeltaId: 1, status: 'ok'}}
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
    const w = wrapper({ wfModule: null })
    expect(w).toMatchSnapshot()
    expect(w.find('TableView')).toHaveLength(1)
  })

  it('renders an iframe when htmlOutput', () => {
    const w = wrapper({ htmlOutput: true })
    expect(w.find(OutputIframe).prop('visible')).toBe(true)
  })

  it('renders different table than iframe when desired', () => {
    const w = wrapper({
      wfModuleBeforeError: { id: 1, lastRelevantDeltaId: 2 },
      wfModule: { id: 3, lastRelevantDeltaId: 4, status: 'error' }
    })
    expect(w.find('TableView').prop('wfModuleId')).toEqual(1)
    expect(w.find('TableView').prop('lastRelevantDeltaId')).toEqual(2)
    expect(w.text()).toMatch(/This was the data that led to an error./)
    expect(w.find(OutputIframe).prop('wfModuleId')).toEqual(3)
    expect(w.find(OutputIframe).prop('lastRelevantDeltaId')).toEqual(4)
  })
})
