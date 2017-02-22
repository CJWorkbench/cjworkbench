'use strict';

var DataGrid  = require('../DataGrid')
var React     = require('react/addons')
var TestUtils = React.addons.TestUtils

var testUtils = require('../utils')

var render        = testUtils.render
var findWithClass = testUtils.findWithClass
var tryWithClass  = testUtils.tryWithClass
var generateMockData = testUtils.generateMockData

var SELECTED_CLASSNAME = 'z-selected'
var ROW_CLASSNAME = 'z-row'

var columns = [
    { name: 'index', title: '#', width: 50 },
    { name: 'firstName'},
    { name: 'lastName'  },
    { name: 'city' },
    { name: 'email' }
];

function checkSelected(row, value){
    React.findDOMNode(row)
        .className.includes(SELECTED_CLASSNAME)
        .should.be[value]
}

describe('DataGrid Test Suite - Selection', function() {

    it('Check multiple selection works', function() {

        var data = generateMockData({
            type : 'local',
            len : 10
        })
        data.length.should.equal(10)

        // table with column menu
        var table = render(
            DataGrid({
                idProperty: 'id',
                dataSource: data,
                columns   : columns,
                style: {height: 1000},
                defaultSelected  : {0: true, 1: true}
            })
        )

        var rows = tryWithClass(table, ROW_CLASSNAME)

        rows.length
            .should.equal(10)

        checkSelected(rows[0], true)
        checkSelected(rows[1], true)
        checkSelected(rows[2], false)

        TestUtils.Simulate.click(React.findDOMNode(rows[2]))

        checkSelected(rows[0], false)
        checkSelected(rows[1], false)
        checkSelected(rows[2], true)
    })

})