import React from 'react'
import { ImportModuleFromGitHub }  from './ImportModuleFromGitHub'
import { mount, ReactWrapper } from 'enzyme'
import { okResponseMock } from './test-utils'
import { mockStore } from "./workflow-reducer";

describe('ImportModuleFromGitHub', () => {

  var wrapper;
  var modalLink;
  var reloadModules;
  var api = {
    importFromGithub: okResponseMock()
  };

  beforeEach(() => {
    api = {
      importFromGithub: okResponseMock()
    };
    reloadModules = jest.fn();
    wrapper = mount(
      <ImportModuleFromGitHub
        closeModal={()=>{}}
        reloadModules={reloadModules}
        api={api}
      />
    )
  });

  afterEach(() => wrapper.unmount());

  it('makes API call when github URL submitted', (done) => {
    let modal = wrapper.find('div.modal-dialog');
    expect(modal).toHaveLength(1);

    // For the moment, test the logic by calling handleSubmit
    let event = {
      preventDefault: ()=>{}
    };
    const url = 'http://github.com/somemodule';
    wrapper.setState({url: url});

    // find Import button and click it
    const importButton = modal.find('button[name="import"]');
    expect(importButton).toHaveLength(1);
    importButton.simulate('click');
    
    expect(api.importFromGithub).toHaveBeenCalledWith({ url: url })

    // resolve api promise; see that it refreshes module lib
    setImmediate(() => {
      wrapper.update();
      expect(reloadModules).toHaveBeenCalled();
      done();
    });
  });

});
