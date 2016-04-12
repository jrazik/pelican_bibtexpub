"""
Pelican BibTeX
==============

A Pelican plugin that populates the context with a list of formatted
citations, loaded from a BibTeX file at a configurable path.

The use case for now is to generate a ``Publications'' page for academic
websites.
"""
# Author: Vlad Niculae <vlad@vene.ro>
# Unlicense (see UNLICENSE for details)

from pelican import signals

import logging
logger = logging.getLogger(__name__)

import os
from operator import itemgetter
from docutils import nodes
from docutils.parsers.rst import directives, Directive

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

try:
    from pybtex.database.input.bibtex import Parser
    from pybtex.database.output.bibtex import Writer
    from pybtex.database import BibliographyData, PybtexError
    from pybtex.backends import html
    from pybtex.style.formatting import jo
except ImportError:
    logger.warn('`pelican_bibtex` failed to load dependency `pybtex`')


from jinja2 import Environment, FileSystemLoader
from pelican import signals

__version__ = '0.2.1'


class Publications(Directive):

    required_arguments = 1
    optional_arguments = 1
    has_content = False
    final_argument_whitespace = False
    option_spec = {
        # 'sort': sort,
        'template': directives.path,
        # 'strong': directives.unchanged,
    }

    def run(self):
        refs_file = self.arguments[0].strip()

        try:
            bibdata_all = Parser().parse_file(refs_file)
        except PybtexError as e:
            logger.warn('`pelican_bibtex` failed to parse file %s: %s' % (
                refs_file,
                str(e)))
            return

        # format entries
        jo_style = jo.Style()
        jo_style.strong = 'Razik'
        html_backend = html.Backend()
        formatted_entries = jo_style.format_entries(bibdata_all.entries.values())

        publications = []

        for formatted_entry in formatted_entries:
            key = formatted_entry.key
            entry = bibdata_all.entries[key]
            year = entry.fields.get('year')
            # This shouldn't really stay in the field dict
            # but new versions of pybtex don't support pop
            pdf = entry.fields.get('pdf', None)
            slides = entry.fields.get('slides', None)
            poster = entry.fields.get('poster', None)

            # render the bibtex string for the entry
            bib_buf = StringIO()
            bibdata_this = BibliographyData(entries={key: entry})
            Writer().write_stream(bibdata_this, bib_buf)
            text = formatted_entry.text.render(html_backend)

            publications.append((key,
                                 year,
                                 text,
                                 bib_buf.getvalue(),
                                 pdf,
                                slides,
                                 poster))

        # Load the publications template
        if 'template' in self.options:
            template_path = self.options['template']
            template_dir, template_name = os.path.split(template_path)
            env = Environment(loader=FileSystemLoader(template_dir))
            template = env.get_template(template_name)
        else:
            # Use template from the Pelican theme
            template = pelican_generator.get_template('publications')

        rendered_template = template.render(publications=publications)
        return [nodes.raw('', rendered_template, format='html')]

pelican_generator = None


def get_template_env(generator):
    global pelican_generator
    pelican_generator = generator


def register():
    # Register new RST directive
    directives.register_directive('publications', Publications)
    # Connect to Pelican generator init to get access
    # to the template environment.
    signals.generator_init.connect(get_template_env)
