'use strict';

var getDateParamKey = require('./getDateParamKey');

function deleteDateParam(params, key) {
  delete params[getDateParamKey(params, key)];
}

module.exports = deleteDateParam;