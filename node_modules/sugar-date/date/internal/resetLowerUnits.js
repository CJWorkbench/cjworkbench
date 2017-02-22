'use strict';

var getLowerUnitIndex = require('./getLowerUnitIndex'),
    setUnitAndLowerToEdge = require('./setUnitAndLowerToEdge');

function resetLowerUnits(d, unitIndex) {
  return setUnitAndLowerToEdge(d, getLowerUnitIndex(unitIndex));
}

module.exports = resetLowerUnits;