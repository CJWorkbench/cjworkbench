import React from 'react'
import { ImportModuleFromGitHub }  from './ImportModuleFromGitHub'
import { mount, ReactWrapper } from 'enzyme'
import { okResponseMock } from './test-utils'
import { mockStore } from "./workflow-reducer";

//FIXME upgrade to react v16 then test these modals
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
    let modal = wrapper.find('.modal-dialog');
    expect(modal).toHaveLength(1);

    // For the moment, test the logic by calling handleSubmit
    let event = {
      preventDefault: ()=>{}
    };
    let url = 'http://github.com/somemodule';
    wrapper.setState({url: url});

    wrapper.instance().handleSubmit(event);

    expect(api.importFromGithub).toHaveBeenCalled();
    expect(api.importFromGithub.mock.calls[0][0]).toEqual({url: url});

    // resolve api promise; see that it refreshes module lib
    setImmediate(() => {
      wrapper.update();
      expect(reloadModules).toHaveBeenCalled();
      done();
    });

    // FIXME upgrade to React v16 and reactstrap v5 so we can get portal contents, and uncomment
    // // find Import button and click it
    // let importButton = modal.find('.action-button');
    // expect(importButton).toHaveLength(1);
    // importButton.simulate('click');
    //
    // expect(api.importFromGithub.mock.calls.length).toBe(1);
  });

});
