/*
 * Inter-process communication format.
 *
 * Thrift objects make a low-level serialization format. This helps us build
 * safe APIs in multiple languages. Each language should have a higher-level
 * type hierarchy that can be converted to and from these low-level types.
 */

namespace py cjwkernel.thrift

/**
 * The module's code is invalid, as per its programming language.
 */
struct ModuleErrorCompileError {
  /** Compiler error message. */
  1: string message
}

/** A module's code took too long to execute. */
struct ModuleErrorTimeout {
  /** How long we were configured to wait. */
  1: double max_seconds,

  /** Last few lines of console output before termination. */
  2: string log
}

/** A module's code terminated unexpectedly. */
struct ModuleErrorExited {
  /**
   * Exit code; must be non-zero.
   *
   * Exit code 137 means we were sent 'kill -9' ... which often means, "out of
   * memory".
   */
  1: i16 exit_code, // Thrift doesn't have a uint8 type

  /** Last few lines of console output before exit. */
  2: string log
}

/**
 * Validation of a kernel module's code succeeded.
 *
 * This value cannot be trusted: a malicious module may report that it is ok.
 * (Indeed, many buggy modules _will_ self-report as ok.)
 */
struct ValidateModuleResultOk {
}

/**
 * Validation of a kernel module's code failed.
 *
 * `compile_error` and `timeout` can be trusted: a malicious module cannot
 * fake them. `exited` can be manipulated by a malicious module, though there
 * doesn't seem to be much point.
 */
union ValidateModuleResultError {
  /** The kernel module's code cannot be run. */
  1: ModuleErrorCompileError compile_error,

  /**
   * The kernel module's code took too long to run.
   *
   * In Python code, this can happen if there's a long-running block of code at
   * the top level of the module.
   */
  2: ModuleErrorTimeout timeout,

  /**
   * The kernel module's code exited with a non-zero exit code.
   *
   * During module load, Workbench will execute the module code. The module
   * will then self-validate and exit with status code 1 if it detects, say,
   * that its `render()` function has the wrong signature.
   *
   * Do not trust this return value: it is returned by the module itself after
   * user code was run. The intent is for well-meaning code to self-diagnose
   * with a helpful error message. Malicious code will ... uh ...
   * self-diagnose with an *un*-helpful error message.
   */
  3: ModuleErrorExited exited
}

/**
 * Result of attempting to load and run module code.
 *
 * An `ok` result does not mean the module can be _trusted_. No module code can
 * be trusted. An `error` result _always_ means the module can't be trusted.
 */
union ValidateModuleResult {
  1: ValidateModuleResultOk ok,
  2: ValidateModuleResultError error
}

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
 * Table stored on disk, ready to be mmapped.
 *
 * The file on disk is `{tab_slug}.arrow`, in a directory agreed upon by the
 * processes passing this data around.
 */
struct ArrowTable {
  /** Unique tab identifier.
   *
   * There must be a valid Arrow file on disk named after `tab_slug`.
   */
  1: string tab_slug,

  /**
   * Columns in the table.
   *
   * The Arrow file's columns must agree with these columns.
   */
  2: list<Column> columns,
}

/** Module `render()` and `fetch()` parameters. */
struct Params {
  /**
   * JSON-encoded dictionary of values.
   *
   * Must be a valid JSON dictionary.
   */
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
 * another. This only happens if the output was a `RenderResultOk` with a
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
  2: Params partial_params,
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
 * The module executed a Step's render() without crashing.
 *
 * An "ok" result may be a user-friendly error -- that is, a zero-column table
 * and non-empty `errors`.
 */
struct RenderResultOk {
  /**
   * Table the Step outputs.
   *
   * If the Step output is "error, then the table must have zero columns.
   */
  1: ArrowTable table, // zero columns if error/undefined

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
 * The module executed, but its output did not pass validation.
 *
 * This is always a bug in the module code. Module code must always return
 * RenderResultOk and then exit. Here are the errors a module may have that
 * would cause "invalid output":
 *
 * * The module did not write exactly one object to its output channel.
 * * The module wrote a non-RenderResultOk object to the output channel.
 * * The module wrote RenderResultOk, but its `table` or `json` were invalid.
 */
struct RenderResultErrorInvalidOutput {
  1: string message
}

/**
 * A bug in the module prevented this Step from completing.
 *
 * This should always email someone. Buggy modules affect users.
 */
union RenderResultError {
  /** The module exited with exit code 0 but did not write valid output. */
  1: RenderResultErrorInvalidOutput invalid_output,

  /** The module did not exit in time. */
  2: ModuleErrorTimeout timeout,

  /** The module exited with a non-zero status code. */
  3: ModuleErrorExited exited
}

/**
 * The outcome of a call to `render()`.
 */
union RenderResult {
  /**
   * The module did not crash.
   *
   * (This could be an error message for the user.)
   */
  1: RenderResultOk ok,

  /**
   * The module crashed.
   *
   * This is always a bug. Email someone.
   */
  2: RenderResultError error
}

/**
 * Interface encapsulating a module (user code).
 */
service KernelModule {
  ValidateModuleResult validateModule(),

  Params migrateParams(
      1: Params params
  ),

  /**
   * Render a single Step.
   */
  RenderResult render(
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
  )
}
