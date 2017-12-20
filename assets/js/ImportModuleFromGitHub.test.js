import React from 'react'
import ImportModuleFromGitHub  from './ImportModuleFromGitHub'
import { mount, ReactWrapper } from 'enzyme'

describe('ImportModuleFromGitHub', () => {

  var wrapper;  
  var modalLink;

  beforeEach(() => wrapper = mount(
    <ImportModuleFromGitHub
      moduleLibrary={{}}
      moduleAdded={()=>{}}
    />
  ));
  beforeEach(() => modalLink = wrapper.find('.import-module-button'));    

  it('Link will open modal window', () => { 
    expect(wrapper).toMatchSnapshot();

    expect(wrapper.state().modalOpen).toBe(false)
    
    expect(modalLink).toHaveLength(1);
    modalLink.simulate('click');
    expect(wrapper.state().modalOpen).toBe(true);

    // The insides of the Modal are a "portal", that is, attached to root of DOM, not a child of Wrapper
    // So find them, and make a new Wrapper
    // Reference: "https://github.com/airbnb/enzyme/issues/252"
    let modal_element = document.getElementsByClassName('modal-dialog');
    expect(modal_element.length).toBe(1);
    let modal = new ReactWrapper(modal_element[0], true)
    expect(modal).toMatchSnapshot();
    expect(modal.find('.dialog-body')).toHaveLength(1);

  });
    
});

