'use strict';

var el

module.exports = function(){

	if(!el && !!global.document){
	  	el = global.document.createElement('div')
	}

	if (!el){
		el = {style: {}}
	}

	return el
}