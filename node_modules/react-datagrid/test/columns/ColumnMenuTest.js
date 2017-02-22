'use strict';

//ensure DOM environment
require('../testdom')()

var should = require('should')

var React     = require('react/addons')
var TestUtils = React.addons.TestUtils
var DataGrid  = require('../DataGrid')

var TABLE_CLASS         = 'z-table'
var ROW_CLASS           = 'z-row'
var CELL_CLASS          = 'z-cell'
var CELLTEXT_CLASS      = 'z-text'
var COLUMN_HEADER_CLASS = 'z-column-header'
var COL_MENU_BTN        = 'z-show-menu'

var testUtils = require('../utils')

var render        = testUtils.render
var findWithClass = testUtils.findWithClass
var tryWithClass  = testUtils.tryWithClass

describe('DataGrid Test Suite - Columns', function(){


    xit('check column menu should be displayed',function() {

        var data = [{ id: 0, index: 1, firstName: 'John', city: 'London', email: 'jon@gmail.com'}];
        var columns = [
            { name: 'index', title: '#', width: 50 },
            { name: 'firstName'},
            { name: 'lastName'  },
            { name: 'city' },
            { name: 'email' }
        ];

        // table with column menu
        var grid = render(
            DataGrid({
                idProperty    : 'id',
                dataSource    : data,
                columns       : columns,
                withColumnMenu: true
            })
        );

        var showMenuNodes = tryWithClass(grid, COLUMN_HEADER_CLASS)
            .map(function(header){
                return findWithClass(header, 'z-show-menu')
            })

        should(showMenuNodes.length)
            .equal(5)
    })

})
