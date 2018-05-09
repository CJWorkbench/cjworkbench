import React from 'react'
import WfModuleContextMenu  from './WfModuleContextMenu'
import { mount, ReactWrapper } from 'enzyme'


describe('WfModuleContextMenu', () => {

  let wrapper
  let removeModule
  
  beforeEach(() => {
    removeModule = jest.fn()

    wrapper = mount(
      <WfModuleContextMenu
        removeModule={removeModule} 
        stopProp={ () => {} }
        id={415}
        className="menu-test-class"        
      />
    )
  })
  afterEach(() => wrapper.unmount())

  it('should match snapshot', () => {
    expect(wrapper).toMatchSnapshot()
  })

  // only checking the call to removeModule(), not the removal
  it('Renders menu option to Delete with onClick method', () => { 
    const deleteButton = wrapper.find('DropdownItem.test-delete-button');
    expect(deleteButton).toHaveLength(1);
    deleteButton.simulate('click');
    expect(removeModule).toHaveBeenCalled()
  });

  // FIXME upgrade to React v16 and reactstrap v5 and uncomment these tests
  //describe('Modal window', () => {
  //  
  //  let modal;
  //  
  //  beforeEach( () => {
  //    // open the modal window
  //    let exportButton = wrapper.find('.test-export-button');
  //    exportButton.simulate('click');
  //    // The insides of the Modal are a "portal", that is, attached to root of DOM, not a child of Wrapper
  //    // So find them, and make a new Wrapper
  //    // Reference: "https://github.com/airbnb/enzyme/issues/252"
  //    let modal_element = document.getElementsByClassName('menu-test-class');
  //    modal = new ReactWrapper(modal_element[0], true)
  //  });
  //  
  //  it('Modal links render correctly, and Done button closes modal', () => { 

  //    expect(wrapper.state().exportModalOpen).toBe(true);

  //    expect(modal).toMatchSnapshot();
  //    expect(modal.find('.dialog-body')).toHaveLength(1);

  //    // check that links have rendered correctly
  //    let csvField = modal.find('.test-csv-field');
  //    expect(csvField.length).toBe(1);
  //    expect(csvField.props().placeholder).toBe("/public/moduledata/live/415.csv");

  //    let jsonField = modal.find('.test-json-field');
  //    expect(jsonField.length).toBe(1);
  //    expect(jsonField.props().placeholder).toBe("/public/moduledata/live/415.json");

  //    let doneButton = modal.find('.test-done-button');
  //    expect(doneButton.length).toBe(1);
  //    doneButton.simulate('click');

  //    expect(wrapper).toMatchSnapshot();
  //    expect(wrapper.state().exportModalOpen).toBe(false)
  //  });

  //  it('Renders modal links which can be copied to clipboard', () => { 
  //    let csvCopy = modal.find('.test-csv-copy');
  //    expect(csvCopy).toHaveLength(1);
  //          
  //    let jsonCopy = modal.find('.test-json-copy');
  //    expect(jsonCopy).toHaveLength(1);       
  //    
  //  });

  //  it('Renders modal links which can be downloaded', () => {
  //    let csvDownload = modal.find('.test-csv-download');
  //    expect(csvDownload).toHaveLength(1);
  //    expect(csvDownload.props().href).toBe("/public/moduledata/live/415.csv");      
  //    
  //    let jsonDownload = modal.find('.test-json-download');
  //    expect(jsonDownload).toHaveLength(1);
  //    expect(jsonDownload.props().href).toBe("/public/moduledata/live/415.json");      
  //  });

  //});
  
});




