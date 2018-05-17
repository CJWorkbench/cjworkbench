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
    const deleteButton = wrapper.find('button.test-delete-button');
    expect(deleteButton).toHaveLength(1);
    deleteButton.simulate('click');
    expect(removeModule).toHaveBeenCalled()
  });

  describe('Modal window', () => {
    
    let modal;
    
    beforeEach( () => {
      // open the modal window
      const exportButton = wrapper.find('button.test-export-button');
      exportButton.simulate('click');
      modal = wrapper.find('div.modal-dialog');
    });

    it('should render modal according to snapshot', () => {
      expect(wrapper.state().exportModalOpen).toBe(true);
      expect(modal).toMatchSnapshot();
    })
    
    it('should render modal links', () => { 
      // check that links have rendered correctly
      const csvField = modal.find('input.test-csv-field');
      expect(csvField.length).toBe(1);
      expect(csvField.props().placeholder).toBe("/public/moduledata/live/415.csv");

      const jsonField = modal.find('input.test-json-field');
      expect(jsonField.length).toBe(1);
      expect(jsonField.props().placeholder).toBe("/public/moduledata/live/415.json");
    });

    it('should close modal', () => {
      const doneButton = modal.find('button.test-done-button');
      doneButton.simulate('click');
      expect(wrapper.state().exportModalOpen).toBe(false)
    })

    it('Renders modal links which can be copied to clipboard', () => { 
      const csvCopy = modal.find('div.test-csv-copy');
      expect(csvCopy).toHaveLength(1);
            
      const jsonCopy = modal.find('div.test-json-copy');
      expect(jsonCopy).toHaveLength(1);       
      
    });

    it('Renders modal links which can be downloaded', () => {
      const csvDownload = modal.find('a.test-csv-download');
      expect(csvDownload.prop('href')).toBe("/public/moduledata/live/415.csv");      
      
      const jsonDownload = modal.find('a.test-json-download');
      expect(jsonDownload.prop('href')).toBe("/public/moduledata/live/415.json");      
    });

  });
});
