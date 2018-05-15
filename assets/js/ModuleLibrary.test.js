/**
 * Testing Stories:
 * -In not-read-only, renders <ModuleLibraryOpen> by default in not-read-only
 * -When read-only, renders <ModuleLibraryClosed> without modules.
 *
 */

import React from 'react'
import { ModuleLibrary } from './ModuleLibrary'
import { shallow } from 'enzyme'
import { genericTestModules } from './test-utils'

describe('ModuleLibrary', () => {
  let wrapper;
  let api;
  let stubs;

  let workflow = {
    "id":15,
    "name":"What a workflow!",
  };

  beforeEach(() => {
    stubs = {
      setLibraryOpen: jest.fn(),
      addModule: jest.fn(),
      dropModule: jest.fn(),
      setWfLibraryCollapse: jest.fn(),
    }
  });

  it('deals with empty modules', ()=>{
    // this can happen on first mount; don't crash
    wrapper = shallow(
      <ModuleLibrary
        {...stubs}
        api={{}}
        modules={undefined}
        workflow={workflow}
        isReadOnly={true}
        libraryOpen={true}
        />
    );
    expect(wrapper.state().modules).toEqual([])
  });


  describe('Not Read-only', () => {
    beforeEach(() => {
      api = {
        setWfLibraryCollapse: jest.fn(),
      };
      wrapper = shallow(
        <ModuleLibrary
          {...stubs}
          modules={genericTestModules}
          api={api}
          workflow={workflow}
          isReadOnly={false}
          libraryOpen={true}
          />
      )
    });

    it('matches snapshot', () => {
      expect(wrapper).toMatchSnapshot()
    });

    it('loads modules', () => {
      const moduleLibraryOpen = wrapper.find('ModuleLibraryOpen');
      expect(moduleLibraryOpen).toHaveLength(1); // is open
      expect(moduleLibraryOpen.props().modules).toHaveLength(genericTestModules.length);

      expect(wrapper.find('ModuleLibraryOpen').props().modules).toEqual(genericTestModules);
    })
  });

  describe('Read-only', () => {
    beforeEach(() => {
      api = {
        setWfLibraryCollapse: jest.fn(),
      };
      wrapper = shallow(
        <ModuleLibrary
          {...stubs}
          api={api}
          modules={genericTestModules}
          workflow={workflow}
          isReadOnly={true}
          libraryOpen={true}
          />
      )
    });

    it('matches snapshot', () => {
      expect(wrapper).toMatchSnapshot()
    });

    it('loads modules', () => {
      const moduleLibraryClosed = wrapper.find('ModuleLibraryClosed');
      expect(moduleLibraryClosed).toHaveLength(1); // is open
      expect(moduleLibraryClosed.props().modules).toHaveLength(genericTestModules.length);

      expect(wrapper.find('ModuleLibraryClosed').props().modules).toEqual(genericTestModules);
    });

  });

});
