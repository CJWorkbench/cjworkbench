'use strict';

var EnglishLocaleBaseDefinition = require('../var/EnglishLocaleBaseDefinition'),
    simpleMerge = require('../../common/internal/simpleMerge'),
    simpleClone = require('../../common/internal/simpleClone');

function getEnglishVariant(v) {
  return simpleMerge(simpleClone(EnglishLocaleBaseDefinition), v);
}

module.exports = getEnglishVariant;