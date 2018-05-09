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
        wrapper.update()
        expect(wrapper).toMatchSnapshot();

        // check that col names have loaded and turned into disabled checkboxes
        expect(wrapper.state().colNames).toEqual(testcols);
        let checkboxList = wrapper.find('input[disabled=true]');
        expect(checkboxList).toHaveLength(6);

        // check that select all/none buttons are disabled
        let buttonList = wrapper.find('button[disabled=true]');
        expect(buttonList).toHaveLength(2);

        expect(wrapper.state().selected).toEqual(["foo", "bar", "baz"]);

        done();
      });
    });


  });

  describe('NOT Read-only', () => {

    var wrapper;

    beforeEach(() => {
      wrapper = mount(
        <ColumnSelector
          selectedCols='foo,bar,baz'
          getColNames={ () => { return Promise.resolve(testcols) } }
          saveState={ () => {} }
          revision={101}
          isReadOnly={false}
        />
      );
    });

    it('Loads and renders column names', (done) => {
      setImmediate(() => {
        wrapper.update()
        expect(wrapper).toMatchSnapshot();

        // check that col names have loaded and turned into checkboxes
        expect(wrapper.state().colNames).toEqual(testcols);
        let checkboxList = wrapper.find('input');
        expect(checkboxList).toHaveLength(6);

        expect(wrapper.state().selected).toEqual(["foo", "bar", "baz"]);
        done();
      });
    });

    it('Changes selected columns on click', (done) => {
      setImmediate(() => {
        wrapper.update()
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

        setImmediate( () => {
          wrapper.update()
          // selected items should be the same
          expect(wrapper.state().selected).toEqual(["foo", "bar", "baz", 'wow']);

          done();
        });
      });
    });

    it('selects all columns when "select all" is clicked', (done) => {
      setImmediate(() => {
        wrapper.update()
        expect(wrapper.state().selected).toEqual(["foo", "bar", "baz"]);

        let selectAllButton = wrapper.find('button.mc-select-all');
        selectAllButton.simulate('click');
        expect(wrapper.state().selected).toEqual(testcols);
        done();
      });
    });

    it('deselects all columns when "select none" is clicked', (done) => {
      setImmediate(() => {
        wrapper.update()
        expect(wrapper.state().selected).toEqual(["foo", "bar", "baz"]);

        let selectNoneButton = wrapper.find('button.mc-select-none');
        selectNoneButton.simulate('click');
        expect(wrapper.state().selected).toEqual([]);
        done();
      });
    })
  });
});
