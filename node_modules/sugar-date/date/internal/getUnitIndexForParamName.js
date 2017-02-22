'use strict';

var iterateOverDateParams = require('./iterateOverDateParams');

function getUnitIndexForParamName(name) {
  var params = {}, unitIndex;
  params[name] = 1;
  iterateOverDateParams(params, function(name, val, unit, i) {
    unitIndex = i;
    return false;
  });
  return unitIndex;
}

module.exports = getUnitIndexForParamName;