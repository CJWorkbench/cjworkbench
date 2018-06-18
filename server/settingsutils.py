# Utilities that are needed in our settings.py

# How usernames are displayed throughout the system, including UI and emails
def workbench_user_display(user):
    if user is None:
        return 'Anonymous'
    elif user.first_name or user.last_name:
        return ('%s %s' % (user.first_name, user.last_name)).strip()
    elif hasattr(user, 'email'):
        return user.email
    else:
        return '(unknown)'

# If the user's name is going to be displayed publicly, never use email
def workbench_user_display_public(user):
    if user is None:
        return 'Anonymous'
    elif user.first_name or user.last_name:
        return ('%s %s' % (user.first_name, user.last_name)).strip()
    else:
        return 'Unnamed User'
