'use strict';

var toUpperFirst = require('./toUpperFirst')
var prefixes     = ["ms", "Moz", "Webkit", "O"]

var el = require('./el')

var ELEMENT
var PREFIX

module.exports = function(key){

	if (PREFIX !== undefined){
		return PREFIX
	}

	ELEMENT = ELEMENT || el()

	var i = 0
	var len = prefixes.length
	var tmp
	var prefix

	for (; i < len; i++){
		prefix = prefixes[i]
		tmp = prefix + toUpperFirst(key)

		if (typeof ELEMENT.style[tmp] != 'undefined'){
			return PREFIX = prefix
		}
	}

	return PREFIX
}