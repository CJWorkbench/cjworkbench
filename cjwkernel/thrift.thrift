/*
 * Inter-process communication format.
 *
 * Thrift objects make a low-level serialization format. This helps us build
 * safe APIs in multiple languages. Each language should have a higher-level
 * type hierarchy that can be converted to and from these low-level types.
 */

namespace py cjwkernel.thrift

/**
 * Validation of a kernel module's code succeeded.
 *
 * This value cannot be trusted: a malicious module may report that it is ok.
 * (Indeed, many buggy modules _will_ self-report as ok.)
 */
struct ValidateModuleResult {}

/** A "text"-typed column. */
struct ColumnTypeText {
}

/** A "number"-typed column. */
struct ColumnTypeNumber {
  /** Python-syntax number format, like `{,.2%}` */
  1: string format = "{:,}"
}

/** A "datetime"-typed column. */
struct ColumnTypeDatetime {
  /* TODO add a `format` */
}

/**
 * The type (and its options) of a column.
 *
 * This is the _user-visible_ type. We do not store the bit layout. For
 * instance, we store "number" and not "i32" or "i64".
 */
union ColumnType {
  1: ColumnTypeText text_type,
  2: ColumnTypeNumber number_type,
  3: ColumnTypeDatetime datetime_type
}

/** Description of a column in a table. */
struct Column {
  /** Name of the column (unique among all columns in the table). */
  1: string name,

  /** Date type the user will see. */
  2: ColumnType type
}

/**
 * Table data that will be cached for easy access.
 */
struct TableMetadata {
  /** Number of rows in the table. */
  1: i32 n_rows,

  /** Columns -- the user-visible aspects of them, at least. */
  2: list<Column> columns
}

/**
 * Table stored on disk, ready to be mmapped.
 *
 * The file on disk is in a directory agreed upon by the processes passing this
 * data around.
 */
struct ArrowTable {
  /**
   * Name of file on disk that contains data.
   *
   * For a zero-column table, filename may be the empty string -- meaning there
   * is no file on disk. In all other cases, the file on disk must exist.
   */
  1: string filename,

  /** Metadata; must agree with the file on disk. */
  2: TableMetadata metadata
}

/**
 * Table stored on disk, ready to be loaded.
 *
 * The file on disk is in a directory agreed upon by the processes passing this
 * data around.
 */
struct ParquetTable {
  /**
   * Name of file on disk that contains data.
   *
   * For a zero-column table, filename may be the empty string -- meaning there
   * is no file on disk. In all other cases, the file on disk must exist.
   */
  1: string filename,

  /** Metadata; must agree with the file on disk. */
  2: TableMetadata metadata
}

/**
 * Value (or nested value) in Params passed to render()/fetch().
 *
 * These params are connected to the `table` parameter: a "column"-typed
 * parameter will be a `Column`; a "tab"-typed parameter will be a `TabOutput.
 *
 * This is more permissive than module_spec. Callers should validate against
 * the module spec.
 *
 * The special value `None` is allowed. Thrift unions are just structs with
 * optional fields; in this case, if all fields are unset, then that means
 * `null`.
 */
union ParamValue {
  /**
   * String value.
   *
   * This represents "string", "enum" and "file" values. Over the wire, it's
   * all the same to us.
   */
  1: string string_value,
  2: i64 integer_value,
  3: double float_value,
  4: bool boolean_value,
  5: Column column_value,
  6: TabOutput tab_value,
  /**
   * List of nested values.
   *
   * This represents "list", "multicolumn", "multitab" and "multichartseries"
   * dtypes. Over the wire, it's all the same to us.
   */
  7: list<ParamValue> list_value,
  /**
   * Mapping of key to nested value.
   *
   * This represents "map" and "dict" dtypes. Over the wire, it's all the same
   * to us.
   */
  8: map<string, ParamValue> map_value,
}

/**
 * Module `render()` and `fetch()` parameters.
 *
 * These are _basically_ JSON ... but Params can include TabOutput, Column, and
 * others, so JSON doesn't cut it.
 *
 * See `module_spec_schema.yaml` for the data this needs to model.
 *
 * Examples:
 *
 * * `params["slug"].integer_value`
 * * `params["slug"].multicolumn_value[2].name`;
 * * `params["slug"].dict_value["subslug"].column_value.type
 */
typedef map<string, ParamValue> Params

/**
 * Value (or nested value) passed to `migrate_params()`.
 *
 * Raw parameter values are stored in the database as JSON. We pass them using
 * JSON-encoded string. This is not the same as the Thrift type "Params", which
 * is passed to `render()`: Params are objects with TabOutput/Column/etc
 * members.
 */
struct RawParams {
  1: string json
}

/** Tab description. */
struct Tab {
  /** Tab identifier, unique in its Workflow. */
  1: string slug,

  /** Tab name, provided by the user. */
  2: string name
}

/**
 * Already-computed output of a tab.
 *
 * During workflow execute, the output from one tab can be used as the input to
 * another. This only happens if the output was a `RenderResult` with a
 * non-zero-column `table`. (The executor won't run a Step whose inputs aren't
 * valid.)
 */
struct TabOutput {
  /** Tab that was processed. */
  1: Tab tab,

  /**
   * Output from the final Step in `tab`.
   */
  2: ArrowTable table
}

/** Argument to a translatable string. */
union I18nArgument {
  1: string string_value,
  2: i32 i32_value,
  3: double double_value
}

/** Translation key and arguments. */
struct I18nMessage {
  /** Message ID. For instance, `modules.renamecolumns.duplicateColname` */
  1: string id,

  /**
   * Arguments (if Message ID takes any).
   *
   * For instance, `["Old Name", "New Name"]`.
   */
  2: list<I18nArgument> arguments
}

/** Instruction that upon clicking a button, Workbench should create a Step. */
struct PrependStepQuickFixAction {
  /** Module to prepend. */
  1: string module_slug,

  /** Some params to set on the new Step (atop the module's defaults). */
  2: RawParams partial_params,
}

/** Instruction for what happens when the user clicks a Quick Fix button. */
union QuickFixAction {
  /** Clicking the button will add a Step before the button's Step. */
  1: PrependStepQuickFixAction prepend_step,
}

/** Button the user can click in response to an error message. */
struct QuickFix {
  1: I18nMessage button_text,
  2: QuickFixAction action
}

/**
 * Error or warning encountered during `render()`.
 *
 * If `render()` output is a zero-column table, then its result's errors are
 * "errors" -- they prevent the workflow from executing. If `render()` outputs
 * columns, though, then its result's errors are "warnings" -- execution
 * continues and these messages are presented to the user.
 */
struct RenderError {
  1: I18nMessage message,
  2: list<QuickFix> quick_fixes,
}


/**
 * Parameters to `fetch()`.
 */
struct FetchRequest {
  /**
   * User-supplied params.
   */
  1: Params params,

  /**
   * User-supplied secrets.
   */
  2: RawParams secrets,

  /**
   * Result of the previous fetch().
   *
   * This is to support modules that "accumulate" data. Think of their fetch()
   * as a reducer: each time they run, they operate on their previous output.
   * (e.g., Twitter module monitoring a politician's tweets.)
   *
   * A Step may never run two fetches concurrently.
   *
   * Empty on initial call.
   */
  3: optional FetchResult last_fetch_result,

  /**
   * Cached result from previous module's render.
   *
   * This is to support modules that take a column as input. Unfortunately, we
   * have a lot more work to do to make these modules work as expected. (The
   * changes will probably require rewriting all modules that use this
   * feature.) In the meantime, this hack gets some jobs done.
   */
  4: optional ParquetTable input_table,
}

/**
 * The module executed a Step's fetch() without crashing.
 *
 * An "ok" result may be a user-friendly error -- that is, an empty file (or,
 * for backwards compat, a zero-column parquet file) and non-empty `errors`.
 */
struct FetchResult {
  /**
   * File the fetch produced.
   *
   * Currently, this must be a valid Parquet file. In the future, we will
   * loosen the requirement and allow any file.
   *
   * Empty file or zero-column parquet file typically means, "error"; but
   * that's the module's choice and not a hard-and-fast rule.
   */
  1: string filename,

  /**
   * User-facing errors or warnings reported by the module.
   *
   * These are separate from `filename` for two reasons: 1) a convenience for
   * module authors; and 2) so we can run SQL to find common problems.
   */
  2: list<RenderError> errors,
}

/**
 * Parameters to `render()`.
 */
struct RenderRequest {
  /**
   * Output from previous Step.
   *
   * This is zero-row, zero-column on the first Step in a Tab.
   */
  1: ArrowTable input_table,

  /** User-supplied parameters; must match the module's param_spec. */
  2: Params params,

  /** Description of tab being rendered. */
  3: Tab tab,

  /**
   * Other tabs' results, supplied as inputs for this Step.
   *
   * Only user-selected tabs are included here. This is not all rendered
   * tabs: it's only the tabs the user selected in this Step's `tab` and
   * `multitab` parameters.
   */
  4: map<string, TabOutput> input_tabs

  /**
   * Result of latest `fetch`.
   *
   * If unset, `fetch` was never called.
   */
  5: optional FetchResult fetch_result
}

/**
 * The module executed a Step's render() without crashing.
 *
 * An "ok" result may be a user-friendly error -- that is, a zero-column table
 * and non-empty `errors`.
 */
struct RenderResult {
  /**
   * Table the Step outputs.
   *
   * If the Step output is "error, then the table must have zero columns.
   */
  1: ArrowTable table,

  /**
   * User-facing errors or warnings reported by the module.
   */
  2: list<RenderError> errors,

  /**
   * JSON to pass to the module's HTML, if it has HTML.
   *
   * This must be either an empty string, or a valid JSON value.
   */
  3: string json = ""
}

/**
 * Interface encapsulating a module (user code).
 */
service KernelModule {
  ValidateModuleResult validateModule(),
  RawParams migrateParams(1: RawParams params),
  RenderResult render(1: RenderRequest render_request),
  FetchResult fetch(1: FetchRequest fetch_request)
}
