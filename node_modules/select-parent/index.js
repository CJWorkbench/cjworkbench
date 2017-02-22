'use strict';

var curry   = require('./curry')
var matches

module.exports = curry(function(selector, node){

	matches = matches || require('./matches')

    while (node = node.parentElement){
        if (matches.call(node, selector)){
            return node
        }
    }
})