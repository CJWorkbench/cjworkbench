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


/**
 * Migrating params succeeded.
 */
struct MigrateParamsResult {
  1: map<string, Json> params
}

/**
 * JSON-compatible value.
 */
union Json {
  1: string string_value,
  2: i64 int64_value,
  3: double number_value,
  4: bool boolean_value,
  5: list<Json> array_value,
  6: map<string, Json> object_value,
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
  2: string table_filename
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
   * For instance, `{"nColumns": 3, "exampleColumn": "Column X"}`
   */
  2: map<string, I18nArgument> arguments

  /** Pointer to code repository whose catalog translates the message. "library" or "module" */
  3: string source
}

/** Instruction that upon clicking a button, Workbench should create a Step. */
struct PrependStepQuickFixAction {
  /** Module to prepend. */
  1: string module_slug,

  /** Some params to set on the new Step (atop the module's defaults). */
  2: map<string, Json> partial_params,
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
   * Directory where the module will be allowed to read and write.
   *
   * Filenames in the fetch request/response pairs must not contain
   * subdirectories or start with dots; and they must exist within this
   * directory.
   */
  1: string basedir,

  /**
   * User-supplied params.
   */
  2: map<string, Json> params,

  /**
   * User-supplied secrets.
   */
  3: map<string, Json> secrets,

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
  4: optional FetchResult last_fetch_result,

  /**
   * Cached result from previous module's render, if fresh.
   *
   * This is to support modules that take a column as input. Unfortunately, we
   * have a lot more work to do to make these modules work as expected. (The
   * changes will probably require rewriting all modules that use this
   * feature.) In the meantime, this hack gets some jobs done.
   *
   * The file on disk is in the directory, `basedir`, and it is readable.
   */
  5: optional string input_table_parquet_filename,

  /**
   * File where the result should be written.
   *
   * The caller is assumed to have made a best effort to ensure the file is
   * writable.
   *
   * The file on disk is in the directory, `basedir`, and it is writable.
   */
  6: string output_filename,
}

/**
 * The module executed a Step's fetch() without crashing.
 *
 * An "ok" result may be a user-friendly error -- that is, an empty file (or,
 * for backwards compat, a zero-column parquet file) and non-empty `errors`.
 *
 * The module writes the output data to `fetch_request.output_file`.
 *
 * Empty file or zero-column parquet file typically means, "error"; but
 * that's the module's choice and not a hard-and-fast rule.
 */
struct FetchResult {
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
   * Directory on disk where all filenames in this request are to be found.
   *
   * The RenderResponse file is expected to be written here, too.
   *
   * Here's a way to safely reuse this directory after every render(): when
   * sandboxing, mount an OverlayFS with all the input files as read-only,
   * then overlay-mount a "scratch" directory for the module to use (and
   * write to `output_filename`).
   */
  1: string basedir,

  /**
   * Output from previous Step.
   *
   * This is zero-row, zero-column on the first Step in a Tab.
   */
  2: string input_filename,

  /**
   * User-supplied parameters; must match the module's param_schema.
   *
   * `File` params are passed as strings, pointing to temporary files in
   * `basedir`.
   */
  3: map<string, Json> params,

  /** Description of tab being rendered. */
  4: Tab tab,

  /**
   * Result of latest `fetch`.
   *
   * If unset, `fetch` was never called.
   *
   * `fetch_result.filename` will point to a temporary file in `basedir`.
   */
  5: optional FetchResult fetch_result

  /**
   * File where the result Arrow table should be written.
   *
   * The caller is assumed to have made a best effort to ensure the file is
   * writable.
   *
   * The file on disk will be in `basedir`.
   */
  6: string output_filename,

  /**
   * Outputs from other tabs that are inputs into this Step.
   */
  7: list<TabOutput> tab_outputs,
}

/**
 * The module executed a Step's render() without crashing.
 *
 * An "ok" result may be a user-friendly error -- that is, a zero-column table
 * and non-empty `errors`.
 *
 * The module writes the output Arrow data to `render_request.output_file`.
 */
struct RenderResult {
  /**
   * User-facing errors or warnings reported by the module.
   */
  1: list<RenderError> errors,

  /**
   * JSON to pass to the module's HTML, if it has HTML.
   */
  2: map<string, Json> json,
}

/**
 * Interface encapsulating a module (user code).
 */
service KernelModule {
  ValidateModuleResult validateModule(),
  MigrateParamsResult migrateParams(1: map<string, Json> params),
  RenderResult render(1: RenderRequest render_request),
  FetchResult fetch(1: FetchRequest fetch_request)
}
