import React from 'react'
import ColumnSelector from './ColumnSelector'
import { mount } from 'enzyme'

describe('ColumnSelector', () => {

  var wrapper; 
  const testcols = ['foo','bar','baz','wow','word wrap','ok then'];

  describe('Read-only', () => {

    beforeEach(() => wrapper = mount(
      <ColumnSelector
        selectedCols='foo,bar,baz'
        getColNames={ () => { return Promise.resolve(testcols) } }
        saveState={ () => {} }
        revision={101} 
        isReadOnly={true}
      />
    ));
  
    it('Loads and renders disabled column names', (done) => {
      expect(wrapper.state().selected).toEqual(["foo", "bar", "baz"]);

      // need to give chance for componentdidMount to run
      setImmediate( () => {
        expect(wrapper).toMatchSnapshot();

        // check that col names have loaded and turned into disabled checkboxes
        expect(wrapper.state().colNames).toEqual(testcols);
        let checkboxList = wrapper.find('input[disabled=true]');
        expect(checkboxList).toHaveLength(6);

        expect(wrapper.state().selected).toEqual(["foo", "bar", "baz"]);

        done();
      });
    });


  });

  describe('NOT Read-only', () => {

    var wrapper; 

    beforeEach(() => wrapper = mount(
      <ColumnSelector
        selectedCols='foo,bar,baz'
        getColNames={ () => { return Promise.resolve(testcols) } }
        saveState={ () => {} }
        revision={101} 
        isReadOnly={false}
      />
    ));
  
    it('Loads and renders column names', (done) => {
      setImmediate( () => {
        expect(wrapper).toMatchSnapshot();

        // check that col names have loaded and turned into checkboxes
        expect(wrapper.state().colNames).toEqual(testcols);
        let checkboxList = wrapper.find('input');
        expect(checkboxList).toHaveLength(6);

        expect(wrapper.state().selected).toEqual(["foo", "bar", "baz"]);   

        done();
      });
    });

    it('Selected columns change on click', (done) => {
      setImmediate( () => {

        expect(wrapper.state().selected).toEqual(["foo", "bar", "baz"]);

        // filter list to grab one checkbox, and click on it
        // A bit of a pain to synthesize an event in the right format...
        let wowBox = wrapper.find('input[data-name="wow"]');
        expect(wowBox).toHaveLength(1);
        wowBox.simulate('change', {
                          target: {
                            checked: true,
                            attributes : {
                              getNamedItem: () => { return { value: 'wow'} }
                            }
                          }
                        });

        // selected items should be the same
        expect(wrapper.state().selected).toEqual(["foo", "bar", "baz", 'wow']);

        done();
      });
    });

  });

});