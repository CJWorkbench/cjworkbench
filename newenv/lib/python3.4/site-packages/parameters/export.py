
from .parameters import ParameterRange
from .parameters import ParameterTable


def parameters_to_latex(filename, d, indent=0.5):
    lines = []
    tables = []

    def remove_non_valid_characters(lines):
        non_valid_characters = [('_', ' ')]
        if isinstance(lines, list):
            new_lines = []
            for line in lines:
                for non_char in non_valid_characters:
                    line = line.replace(non_char[0], non_char[1])
                new_lines.append(line)
        elif isinstance(lines, str):
            for non_char in non_valid_characters:
                lines = lines.replace(non_char[0], non_char[1])
            new_lines = lines
        return new_lines

    def latex_table(k, v):
        """
        """
        tables.append((k, v))

    def add_latex_tables():
        """
        """
        def write_first_row(content):
            line = ' &'
            for column in content.column_labels():
                line += ' '+column
                line += ' &'
            return line[:-1]

        def write_follwing_rows(content, lines):
            for row in content.rows():
                line = row[0]+' &'
                for value in row[1].values():
                    if isinstance(value, basestring):
                        line += value+' &'
                    else:
                        line += ' %s &' % value
                lines.append(line[:-1]+'\\\ \n')

        for table in tables:
            name, content = table
            pos = 'c'*(len(content.column_labels())+1)
            lines.append('\\begin{table*}[ht]\n')
            lines.append('\\begin{center}\n')
            lines.append('\\begin{tabular}{%s} \n' % pos)
            lines.append(write_first_row(content)+'\\\ \n')
            write_follwing_rows(content, lines)
            lines.append('\\end{tabular} \n')
            lines.append('\\end{center}\n')
            lines.append('\\caption{%s}\n' % name)
            lines.append('\\label{%s}' % name+'\n')
            lines.append('\\end{table*}\n')

    def walk(d, indent, ind_incr):
        """
        """
        s = []
        keys = d.keys()
        keys.sort()
        for key in keys:
            k = key
            v = d[key]
            if hasattr(v, 'items') and not isinstance(v, ParameterTable):
                s.append("\\hspace*{%scm} %s: " % (indent, k))
                s.append(walk(v, indent+ind_incr,  ind_incr))
                s.append('\\hspace*{%scm} ' % indent)
            elif isinstance(v, ParameterRange):
                s.append("\\hspace*{%scm} %s : %s" % (indent, k, str(v._values)))
            elif isinstance(v, ParameterTable):
                s.append("\\hspace*{%scm} %s : see Table~\\ref{%s} " % (indent, k, k))
                latex_table(k, v)
            elif isinstance(v, basestring):
                s.append("\\hspace*{%scm} %s : %s" % (indent, k, v))
            else:
                s.append("\\hspace*{%scm} %s : %s" % (indent, k, v))
        return '\\\ \n'.join(s)

    line = walk(d, 0.0, indent)
    f = open(filename, 'w')
    line = remove_non_valid_characters(line)
    f.write(line)
    f.close()

    add_latex_tables()
    f = open('tables_'+filename, 'w')
    lines = remove_non_valid_characters(lines)
    f.writelines(lines)
    f.close()
