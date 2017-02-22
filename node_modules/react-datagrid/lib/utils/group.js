'use strict';

var hasown = require('hasown');

function copyIf(source, target) {
    var hasOwn = hasown(target);

    Object.keys(source).forEach(function (key) {
        if (!hasOwn(key)) {
            target[key] = source[key];
        }
    });
}

function groupByFields(data, fields, path, names, fieldIndex) {
    data = data || [];
    fieldIndex = fieldIndex || 0;

    var field = fields[fieldIndex];

    if (!field) {
        return data;
    }

    var group = groupArrayByField(data, field);
    var fieldName = typeof field == 'string' ? field : field.name;

    if (!fieldIndex) {
        group.namePath = [];
        group.valuePath = [];
        group.depth = 0;
        delete group.name;
    }

    var groupsCount = group.length;

    if (group.keys && group.keys.length) {

        group.leaf = false;
        group.keys.forEach(function (key) {

            var groupPath = (path || []).concat(key);
            var fieldNames = (names || []).concat(fieldName);
            var data = groupByFields(group.data[key], fields, groupPath, fieldNames, fieldIndex + 1);

            if (Array.isArray(data)) {
                data = {
                    data: data,
                    leaf: true
                };
            }

            data.name = fieldName;
            data.value = key;
            data.valuePath = groupPath;
            data.namePath = fieldNames;
            data.depth = fieldIndex + 1;

            if (typeof field != 'string') {

                copyIf(field, data);
            }

            group.data[key] = data;

            if (!data.leaf) {
                groupsCount += data.groupsCount;
            }
        });
    }

    if (!group.leaf) {
        group.groupsCount = groupsCount;
    }

    return group;
}

function groupArrayByField(data, field) {

    var groupKeys = {};
    var groupKeysArray = [];

    var fieldName = typeof field == 'string' ? field : field.name;(data || []).forEach(function (item) {
        var itemKey = item[fieldName];

        if (groupKeys[itemKey]) {
            groupKeys[itemKey].push(item);
        } else {
            groupKeys[itemKey] = [item];
            groupKeysArray.push(itemKey);
        }
    });

    var result = {
        keys: groupKeysArray,
        data: groupKeys,
        childName: fieldName,
        length: groupKeysArray.length,
        leaf: true
    };

    return result;
}

module.exports = groupByFields;