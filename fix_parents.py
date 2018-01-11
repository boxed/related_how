import os

import django


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "relatedhow.settings")
    django.setup()

    from relatedhow import fix_parents
    fix_parents()


if __name__ == '__main__':
    main()
