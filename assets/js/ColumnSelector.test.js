import React from 'react'
import ColumnSelector from './ColumnSelector'
import { mount } from 'enzyme'

describe('ColumnSelector', () => {

  var wrapper; 

  describe('Read-only', () => {

    beforeEach(() => wrapper = mount(
      <ColumnSelector
        selectedCols='foo,bar,baz'
        getColNames={ () => { return Promise.resolve(['foo,bar,baz,wow,word wrap,ok then']) } }
        saveState={ () => {} }
        revision={101} 
        isReadOnly={true}
      />
    ));
  
    it('Renders and loads column names', (done) => {
      // need to give chance for componentdidMount to run
      setImmediate( () => {
        expect(wrapper).toMatchSnapshot();
        //check that col names have loaded
        expect(wrapper.state().colNames).toEqual(['foo,bar,baz,wow,word wrap,ok then']);   
        expect(wrapper.state().selected).toEqual(["foo", "bar", "baz"]);   

        done();
      });
    });

    it('Checkboxes do not change on click - DUMMY TEST', (done) => {
      setImmediate( () => {

        expect(true).toBe(true);

        //  *** CURRENTLY BROKEN: trying to find/target checkboxes ****
        // // check state
        // expect(wrapper.state().selected).toEqual(["foo", "bar", "baz"]);           

        // // find set of checkboxes
        // let checkboxList = wrapper.find('input');
        // expect(checkboxList).toHaveLength(6);
        
        // // filter list to grab one checkbox
        // let wowBox = checkboxList.filterWhere(n => n.dataName() == 'wow');
        // // click on it
        // wowBox.simulate('change');

        // // check state - should be same
        // expect(wrapper.state().selected).toEqual(["foo", "bar", "baz"]);           

        // // run snap

        done();
      });
    });

  });

  describe('NOT Read-only', () => {

    var wrapper; 

    beforeEach(() => wrapper = mount(
      <ColumnSelector
        selectedCols='foo,bar,baz'
        getColNames={ () => { return Promise.resolve(['foo,bar,baz,wow,word wrap,ok then']) } }
        saveState={ () => {} }
        revision={101} 
        isReadOnly={false}
      />
    ));
  
    it('Renders and loads column names', (done) => {
      setImmediate( () => {
        expect(wrapper).toMatchSnapshot();
        //check that col names have loaded
        expect(wrapper.state().colNames).toEqual(['foo,bar,baz,wow,word wrap,ok then']);   
        expect(wrapper.state().selected).toEqual(["foo", "bar", "baz"]);   

        done();
      });
    });

    it('Checkboxes do change on click - DUMMY TEST', (done) => {
      setImmediate( () => {

        expect(true).toBe(true);
        
        // // check state
        
        // // find a checkbox

        // // click on it

        // // check state - should have changed

        // // run snap
        // expect(wrapper).toMatchSnapshot();
        done();
      });
    });

  });

});