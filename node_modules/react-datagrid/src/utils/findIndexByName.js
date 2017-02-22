'use strict';

var findIndexBy =require('./findIndexBy')

function findIndexByName(arr, name){
    return findIndexBy(arr, function(info){
        return info.name === name
    })
}

module.exports = findIndexByName