import Multichartseries from '../Multichartseries'
import { withJsonStringValues } from '../util'

/**
 * DEPRECATED -- JSON-encoded multi-chart series.
 *
 * Use the non-Custom type 'multichartseries' instead. To migrate to it:
 *
 *    def _migrate_params_v0_to_v1(params):
 *     """
 *     v0: params['y_columns'] is JSON-encoded.
 *
 *     v1: params['y_columns'] is List[Dict[{ name, color }, str]].
 *     """
 *     json_y_columns = params['y_columns']
 *     if not json_y_columns:
 *         # empty str => no columns
 *         y_columns = []
 *     else:
 *         y_columns = json.loads(json_y_columns)
 *     return {
 *         **params,
 *         'y_columns': y_columns
 *     }
 *
 *     def migrate_params(params):
 *         if isinstance(params['y_columns'], str):
 *             params = _migrate_params_v0_to_v1(params)
 *
 *         return params
 *
 * This Custom component may output columns that don't exist, so Python module
 * code will need to handle that case. 'multichartseries' will never send
 * missing columns to Python; so when you transition to 'multichartseries', you
 * may delete a bunch of code and tests.
 */
export default withJsonStringValues(Multichartseries, [])
