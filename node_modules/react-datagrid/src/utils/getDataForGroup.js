'use strict';

/**
 * Returns an array of items that are in the group described
 * by the given keys
 * @param  {String[]/Object[]} keys
 * @param  {Array} [groupData] If none given, this.groupData will be used
 * @return {Array/Undefined} The array with the group items, or undefined if the group is not found.
 *
 * NOTE: an empty array is never returned. If there are no items in the group, it simply means the group
 * does not exist, so undefined is returned
 */
module.exports = function(keys, data){

    if (typeof keys == 'string'){
        keys = [keys]
    }

    var groupData = data

    if (groupData){
        if (keys){
            keys.forEach(function(key){
                if (groupData && groupData.data){
                    groupData = groupData.data[key]
                } else {
                    groupData = undefined
                }
            })
        }

        //If it is undefined we can stop processing here and return
        if (!groupData){
            return groupData
        }

        //otherwise, there are other subgroups in this group
        //so go fetch data from them all and return the result
        var getDeepData = function(group, resultArray){
            var data = group.data
            var keys = group.keys

            if (group.leaf && Array.isArray(data)){
                resultArray.push.apply(resultArray, data)
            } else {
                keys.forEach(function(key){
                    getDeepData(data[key], resultArray)
                })
            }

            return resultArray
        }

        return getDeepData(groupData, [])
    }
}