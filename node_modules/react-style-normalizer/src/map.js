'use strict';

module.exports = function(fn, item){

	if (!item){
		return
	}

	if (Array.isArray(item)){
		return item.map(fn).filter(function(x){
			return !!x
		})
	} else {
		return fn(item)
	}
}