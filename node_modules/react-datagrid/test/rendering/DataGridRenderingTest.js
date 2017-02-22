'use strict';

var DataGrid  = require('../DataGrid')
var React     = require('react/addons')
var TestUtils = React.addons.TestUtils

var TABLE_CLASS         = 'z-table'
var ROW_CLASS           = 'z-row'
var LOADMASK			= 'loadmask'
var COLUMN_HEADER_CLASS = 'z-column-header'
var COL_MENU_BTN        = 'z-show-menu'
var EMPTY_TEXT_CLASS	= 'z-empty-text'
var EMPTY_TEXT 			= 'No records'

var testUtils = require('../utils')

var render        = testUtils.render
var findWithClass = testUtils.findWithClass
var tryWithClass  = testUtils.tryWithClass

describe('DataGrid Test Suite - Rendering', function(){

	it('Check loading controlled prop works as expected',function(done) {

		// empty data array to test loading
		var data = [];

        var columns = [
            { name: 'index', title: '#', width: 50 },
            { name: 'firstName'},
            { name: 'lastName'  },
            { name: 'city' },
            { name: 'email' }
        ];

        var table = render(
        	DataGrid({
                idProperty    : 'id',
                dataSource    : data,
                columns       : columns,
                style		  : { height: 200 },
                loading		  : true
            })
		);

        var loadMask = tryWithClass(table,LOADMASK);
        loadMask.should.not.be.empty

		done()
	})

	it('Check emptyText works',function(done) {

		// empty data array to test empty text
		var data = [];

        var columns = [
            { name: 'index', title: '#', width: 50 },
            { name: 'firstName'},
            { name: 'lastName'  },
            { name: 'city' },
            { name: 'email' }
        ];

        var table = render(
        	DataGrid({
                idProperty    : 'id',
                dataSource    : data,
                columns       : columns,
                style		  : { height: 200 },
                emptyText	  : EMPTY_TEXT
            })
		);

		var emptyText = findWithClass(table,EMPTY_TEXT_CLASS);
		emptyText.should.not.be.empty;
		// check no record text equals with specified text
		emptyText.getDOMNode().textContent.should.equal(EMPTY_TEXT);	

		done()
	})

})