'use strict';

var MULTIPLIERS = require('../var/MULTIPLIERS'),
    DURATION_UNITS = require('../var/DURATION_UNITS'),
    Range = require('./Range'),
    trunc = require('../../common/var/trunc'),
    forEach = require('../../common/internal/forEach'),
    rangeEvery = require('./rangeEvery'),
    simpleCapitalize = require('../../common/internal/simpleCapitalize'),
    defineOnPrototype = require('../../common/internal/defineOnPrototype');

function buildDateRangeUnits() {
  var methods = {};
  forEach(DURATION_UNITS.split('|'), function(unit, i) {
    var name = unit + 's', mult, fn;
    if (i < 4) {
      fn = function() {
        return rangeEvery(this, unit, true);
      };
    } else {
      mult = MULTIPLIERS[simpleCapitalize(name)];
      fn = function() {
        return trunc((this.end - this.start) / mult);
      };
    }
    methods[name] = fn;
  });
  defineOnPrototype(Range, methods);
}

module.exports = buildDateRangeUnits;