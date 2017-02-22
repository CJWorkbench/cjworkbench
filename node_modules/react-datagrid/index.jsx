'use strict';

require('./index.styl')

//var Guid = require('node-uuid')
var sorty = require('sorty')
var React = require('react')
var ReactDOM = require('react-dom')
var DataGrid = require('./src')
var faker = window.faker = require('faker');
var preventDefault = require('./src/utils/preventDefault')

console.log(React.version,' react version');
var gen = (function(){

    var cache = {}

    return function(len){

        if (cache[len]){
            // return cache[len]
        }

        var arr = []

        for (var i = 0; i < len; i++){
            arr.push({
                id       : i + 1,
                // id: Guid.create(),
                grade      : Math.round(Math.random() * 10),
                email    : faker.internet.email(),
                firstName: faker.name.firstName(),
                lastName : faker.name.lastName(),
                birthDate: faker.date.past(),
                country  : faker.address.country(),
                city  : faker.address.city()
            })
        }

        cache[len] = arr

        return arr
    }
})()

var RELOAD = true

var columns = [
    { name: 'index', title: '#', width: 50},
    { name: 'country', width: 200},
    { name: 'city', width: 150 },
    { name: 'firstName' },
    { name: 'lastName'  },
    { name: 'email', width: 200 }
]

var ROW_HEIGHT = 31
var LEN = 2000
var SORT_INFO = [{name: 'country', dir: 'asc'}]//[ { name: 'id', dir: 'asc'} ]
var sort = sorty(SORT_INFO)
var data = gen(LEN);

class App extends React.Component {
    constructor(props, context) {
        super(props, context);
        this.handleSortChange = this.handleSortChange.bind(this);
        this.onColumnResize = this.onColumnResize.bind(this);
    }

    onColumnResize(firstCol, firstSize, secondCol, secondSize) {
        firstCol.width = firstSize
        this.setState({})
    }

    render() {
        return <DataGrid
            ref="dataGrid"
            idProperty='id'
            dataSource={data}
            sortInfo={SORT_INFO}
            onSortChange={this.handleSortChange}
            columns={columns}
            style={{height: 400}}
            onColumnResize={this.onColumnResize}
        />
    }

    handleSortChange(sortInfo) {
        SORT_INFO = sortInfo
        data = sort(data)
        this.setState({})
    }
}

ReactDOM.render((
    <App />
), document.getElementById('content'))
