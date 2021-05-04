# This file should not be executed. Workbench extracts obsolete messages from it.
# Even far into the future, users may see these messages. Translators must
# translate them.
#
# When removing a message or changing its id, move the old message
# (i.e. the call to `i18n.trans()`) here.

# deprecated [2021-05-04]
# The values are all in the rendercache. If we ever clear the rendercache on
# production, we can delete this message.
# i18n: The parameters {found_type} and {best_wanted_type} will have values among "date", "text", "number", "timestamp"; however, including an (possibly empty) "other" case is mandatory.
i18n.trans(
    "py.renderer.execute.types.PromptingError.WrongColumnType.as_quick_fixes.general",
    default="Convert {found_type, select, date {Dates} text {Text} number {Numbers} timestamp {Timestamps} other {}} to {best_wanted_type, select, date {Dates} text {Text} number {Numbers} timestamp {Timestamps} other{}}",
)

# deprecated [2021-05-04]
# The values are all in the rendercache. If we ever clear the rendercache on
# production, we can delete this message.
# i18n: The parameter {columns} will contain the total number of columns that need to be converted; you will also receive the column names: {0}, {1}, {2}, etc. The parameters {found_type} and {best_wanted_type} will have values among "date", "text", "number", "timestamp"; however, including a (possibly empty) "other" case is mandatory.
i18n.trans(
    "py.renderer.execute.types.PromptingError.WrongColumnType.as_error_message.general",
    default="{ columns, plural, offset:2"
    " =1 {The column “{0}” must be converted from { found_type, select, text {Text} number {Numbers} timestamp {Timestamps} other {}} to {best_wanted_type, select, text {Text} number {Numbers} timestamp {Timestamps} other {}}.}"
    " =2 {The columns “{0}” and “{1}” must be converted from { found_type, select, text {Text} number {Numbers} timestamp {Timestamps} other {}} to {best_wanted_type, select, text {Text} number {Numbers} timestamp {Timestamps}  other{}}.}"
    " =3 {The columns “{0}”, “{1}” and “{2}” must be converted from { found_type, select, text {Text} number {Numbers} timestamp {Timestamps} other {}} to {best_wanted_type, select, text {Text} number {Numbers} timestamp {Timestamps} other{}}.}"
    " other {The columns “{0}”, “{1}” and # others must be converted from { found_type, select, text {Text} number {Numbers} timestamp {Timestamps} other {}} to {best_wanted_type, select, text {Text} number {Numbers} timestamp {Timestamps} other{}}.}}",
)
