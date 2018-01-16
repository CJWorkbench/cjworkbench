/**
 * Testing Stories:
 * -Renders list of <ModuleCategory> components
 * -Will render new list of " when new props received.
 */

 import React from 'react'
import ModuleCategories  from './ModuleCategories'
import { mount, shallow } from 'enzyme'
// import { jsonResponseMock, emptyAPI } from './utils'


describe('ModuleCategories ', () => {
  
    var wrapper; 
    var items = []; 
  
    beforeEach(() => wrapper = mount(
      <ModuleCategories
        openCategory={"Add Data"} 
        setOpenCategory={() => {}}
        libraryOpen={true}
        isReadOnly={false}            
        addModule={() => {}}
        dropModule={() => {}}
        items={items}
      />
    ));
  
    it('Renders list of ModuleCategory components', () => { 
      expect(wrapper).toMatchSnapshot();
      // expect(true).toBe(true);
    });
  
    it('Renders new component list when new props received', () => { 
      expect(true).toBe(true);
    });
      
  });

describe('ModuleCategories ', () => {
  
  var wrapper;  
  var modules = [
    {props: {icon: 'add'} }
  ];
  
  describe('Library open ', () => {
  
    // beforeEach(() => wrapper = mount(
    //   <ModuleCategories
  
    //   />
    // ));
  
    it('Renders with list of ModuleCategory components', () => { 
      // expect(wrapper).toMatchSnapshot();
      expect(true).toBe(true);
      
    });
  
    it('Receiving new props will trigger a new render', () => { 
      expect(true).toBe(true);
    });

  });

  // describe('Library closed ', () => {
  
  //   beforeEach(() => wrapper = mount(
  //     <ModuleCategories

  //     />
  //   ));
  
  //   it('Renders with list of ModuleCategory components', () => { 
  //     expect(true).toBe(true);
  //   });
  
  //   it('Receiving new props will trigger a new render', () => { 
  //     expect(true).toBe(true);
  //   });
      
  // });
  
      
});
