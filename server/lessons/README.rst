Coding a Lesson
===============

This directory contains one `.html` file per lesson.

Here are the parts to consider:

Filename
--------

The filename ``your-filename.html`` produces the lesson URL, ``/lessons/your-filename/``. *Don't edit filenames after deploying them*: that would cancel the lesson for everybody who's using it.

Header
------

The HTML file should contain a ``<header>`` like this:

::

  <header>
    <h1>Title</h1>
    <p>Here are some contents.</p>
  </header>

We present the title and contents to the user in the ``/lessons/`` page.

Sections
--------

Each lesson is divided into "sections". Ideally, a section fits in a sidebar without scrolling. It looks like this:

::

  <section>
    <h2>1. This Section's Title</h2>
    <p>Here is some information.</p>
    <p>Here is more information.</p>
    <ol class="steps">
      <li>Do one thing</li>
      <li>Do another thing</li>
      <li>Do a third thing</li>
    </ol>
  </section>

The ``<h2>`` is required: it becomes part of the table of contents. In this example, we gave this section the number ``1``. Numbering is optional. (TODO come up with a lesson style guide.)

The ``<ol class="steps">`` is also required: it describes the step logic. Each step ``<li>`` can contain arbitrary HTML. (TODO add `data-` attributes to the ``<li>`` to make lessons interactive.)

Everything that is not in the ``<h2>`` or ``<ol class="steps">`` is arbitrary HTML: the user will see it between the ``<h2>`` and the ``<ol class="steps">``.