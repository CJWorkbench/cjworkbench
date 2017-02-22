'use strict';

var DateUnits = require('../var/DateUnits'),
    createDate = require('./createDate'),
    mathAliases = require('../../common/var/mathAliases'),
    advanceDate = require('./advanceDate'),
    namespaceAliases = require('../../common/var/namespaceAliases'),
    defineInstanceSimilar = require('../../common/internal/defineInstanceSimilar');

var sugarNumber = namespaceAliases.sugarNumber,
    round = mathAliases.round;

function buildNumberUnitMethods() {
  defineInstanceSimilar(sugarNumber, DateUnits, function(methods, unit) {
    var name = unit.name, base, after, before;
    base = function(n) {
      return round(n * unit.multiplier);
    };
    after = function(n, d, options) {
      return advanceDate(createDate(d, options, true), name, n);
    };
    before = function(n, d, options) {
      return advanceDate(createDate(d, options, true), name, -n);
    };
    methods[name] = base;
    methods[name + 's'] = base;
    methods[name + 'Before'] = before;
    methods[name + 'sBefore'] = before;
    methods[name + 'Ago'] = before;
    methods[name + 'sAgo'] = before;
    methods[name + 'After'] = after;
    methods[name + 'sAfter'] = after;
    methods[name + 'FromNow'] = after;
    methods[name + 'sFromNow'] = after;
  });
}

module.exports = buildNumberUnitMethods;