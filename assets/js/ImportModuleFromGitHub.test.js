/**
 * Testing Stories:
 * -Renders library-open version, which opens to modal
 * -Renders library-closed version, "
 * -Modal will call API to begin import process
 * 
 */

import React from 'react'
import ImportModuleFromGitHub  from './ImportModuleFromGitHub'
import { mount, ReactWrapper } from 'enzyme'
import { jsonResponseMock, okResponseMock } from './utils'

//FIXME upgrade to react v16 then test these modals
describe('ImportModuleFromGitHub', () => {

  var wrapper;
  var modalLink;
  var moduleAdded = jest.fn();
  var api = {
    importFromGithub: okResponseMock()
  };

  beforeEach(() => wrapper = mount(
    <ImportModuleFromGitHub
      closeModal={()=>{}}
      moduleAdded={moduleAdded}
      api={api}
    />
  ));

  afterEach(() => wrapper.unmount())

  it('makes API call when github URL submitted', () => {
    let modal = wrapper.find('.modal-dialog');
    expect(modal).toHaveLength(1);

    // FIXME upgrade to React v16 and reactstrap v5 so we can get portal contents, and uncomment
    // // find Import button and click it
    // let importButton = modal.find('.action-button');
    // expect(importButton).toHaveLength(1);
    // importButton.simulate('click');
    //
    // expect(api.importFromGithub.mock.calls.length).toBe(1);
  });

});
