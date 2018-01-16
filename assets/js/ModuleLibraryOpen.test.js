/**
 * Testing Stories:
 * -Renders full menu with <ModuleSearch>, <ModuleCategories>, <AddNotificationButton>, 
 *    and <ImportModuleFromGitHub> components
 * -Toggle arrow will invoke toggleLibrary() from props
 */

 import React from 'react'
import ModuleLibraryOpen  from './ModuleLibraryOpen'
import { mount, shallow } from 'enzyme'
// import { jsonResponseMock, emptyAPI } from './utils'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'


describe('ModuleLibraryOpen ', () => {

  var wrapper;  
  var items = [];

  beforeEach(() => wrapper = mount(
    <DragDropContextProvider backend={HTML5Backend}>
      <ModuleLibraryOpen
        workflow={{}}
        libraryOpen={true}
        isReadOnly={false}            
        items={items}
        addModule={() => {}}
        dropModule={() => {}}
        moduleAdded={() => {}}
        toggleLibrary={() => {}}
        openLibrary={() => {}}
        openCategory={"Add Data"} 
        setOpenCategory={() => {}}
      />
    </DragDropContextProvider>
  ));

  it('Renders all subcomponents', () => { 
    expect(wrapper).toMatchSnapshot(); 
    // expect(true).toBe(true);
  });

  // it('Toggle arrow will toggle to Closed state', () => { 
  //   expect(true).toBe(true);
  // });
      
});