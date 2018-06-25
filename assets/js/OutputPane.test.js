import React from 'react'
import { shallow } from 'enzyme'
import { OutputPane } from './OutputPane'
import { jsonResponseMock } from './test-utils'
import { OutputIframe } from "./OutputIframe";


describe('OutputPane', () => {
  const wrapper = function(extraProps={}) {
    return shallow(
      <OutputPane
        api={{}}
        workflowId={123}
        revision={1}
        selectedWfModuleId={987}
        isPublic={false}
        isReadOnly={false}
        htmlOutput={false}
        showColumnLetter={false}
        {...extraProps}
        />
    )
  }


  it('Renders', () => {
    const w = wrapper()
    expect(w).toMatchSnapshot()
    expect(w.find('TableView')).toHaveLength(1);
  });

  it('Renders when no module id', () => {
    const w = wrapper({ selectedWfModuleId: null })
    expect(w).toMatchSnapshot();
    expect(w.find('TableView')).toHaveLength(1);
  });

  it('Iframe when htmloutput set', () => {
    const w = wrapper({ htmlOutput: true })
    expect(w.find(OutputIframe)).toHaveLength(1);
    expect(w).toMatchSnapshot();
  });

});


