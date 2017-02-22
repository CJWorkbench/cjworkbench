'use strict';

var isDefined = require('../../common/internal/isDefined'),
    classChecks = require('../../common/var/classChecks'),
    callDateSet = require('../../common/internal/callDateSet'),
    walkUnitDown = require('./walkUnitDown');

var isFunction = classChecks.isFunction;

function setUnitAndLowerToEdge(d, startIndex, stopIndex, end) {
  walkUnitDown(startIndex, function(unit, i) {
    var val = end ? unit.end : unit.start;
    if (isFunction(val)) {
      val = val(d);
    }
    callDateSet(d, unit.method, val);
    return !isDefined(stopIndex) || i > stopIndex;
  });
  return d;
}

module.exports = setUnitAndLowerToEdge;