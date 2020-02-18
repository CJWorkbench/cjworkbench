from django.core.management.base import BaseCommand
import cjwstate.modules
from cjwstate.importmodule import import_module_from_github


class Command(BaseCommand):
    help = "Reimport arguments from https://github.com/CJWorkbench/SLUG.git"

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="+", type=str, help="Name of GitHub repo")

    def handle(self, *args, slugs, **kwargs):
        import subprocess

        subprocess.run(
            ["/app/cjwkernel/setup-sandboxes.sh", "only-readonly"], check=True
        )

        cjwstate.modules.init_module_system()
        for slug in slugs:
            import_module_from_github("CJWorkbench", slug)
