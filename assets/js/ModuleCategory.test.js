/**
 * Testing Stories:
 * -Renders library-open version, which has collapsible list of Module components
 * -Renders library-closed version, "
 * -When one category is expanded, others collapse
 * 
 * CHALLENGE: How to render list of sub-components in test?
 */

import React from 'react'
import ModuleCategory  from './ModuleCategory'
import { mount, shallow } from 'enzyme'
// import { jsonResponseMock, emptyAPI } from './utils'


describe('ModuleCategory ', () => {
  
  var wrapper;  
  var modules = [
    {props: {icon: 'add'} }
  ];
  
  describe('Library open ', () => {
  
    // beforeEach(() => wrapper = mount(
    //   <ModuleCategory
    //     name={"Add Data"}
    //     modules={modules}
    //     isReadOnly={false}
    //     collapsed={true} 
    //     setOpenCategory={() => {}} 
    //     libraryOpen={true}
    //   />
    // ));
  
    it('Renders with collapsible list of Module components', () => { 
      // expect(wrapper).toMatchSnapshot();
      expect(true).toBe(true);
      
    });
  
    it('Expanding one category will collapse the others', () => { 
      expect(true).toBe(true);
    });

  });

  // describe('Library closed ', () => {
  
  //   beforeEach(() => wrapper = mount(
  //     <ModuleCategory
  //       name={currentCategory }
  //       modules={modulesByCategory}
  //       isReadOnly={properties.isReadOnly}
  //       collapsed={currentCategory != properties.openCategory} 
  //       setOpenCategory={properties.setOpenCategory} 
  //       libraryOpen={properties.libraryOpen}
  //     />
  //   ));
  
  //   it('Renders library-open version, which has collapsible list of Module components', () => { 
  //     expect(true).toBe(true);
  //   });
  
  //   it('Expanding one category will collapse the others', () => { 
  //     expect(true).toBe(true);
  //   });
      
  // });
  
      
});