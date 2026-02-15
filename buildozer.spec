[app]

# (str) Title of your application
title = GestionFondosM

# (str) Application versioning (should be a string)
version = 0.1.0

# (str) Package name
package.name = gestionfondos

# (str) Package domain (needed for Android package name)
package.domain = org.gestionfondos

# (str) Source code where the main.py live
source.dir = src

# (str) The entrypoint of the application
# OJO: esto es relativo a source.dir
entrypoint = gf_mobile/main.py

# (list) Exclude files/extensions from packaging
source.exclude_exts = pyc,pyo

# (list) Exclude directories from packaging
source.exclude_dirs = __pycache__

# (list) Application requirements
requirements = python3,kivy,kivymd,sqlalchemy,aiohttp,requests,python-dotenv,python-dateutil,apscheduler,cryptography,keyring,google-auth,google-auth-oauthlib


# Evita usar el recipe legacy de SQLAlchemy (descarga en pypi.python.org -> 404)
p4a.blacklist_requirements = sqlalchemy

# (list) Permissions
android.permissions = INTERNET

# (str) Supported orientation (one of landscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# -------------------------
# ANDROID (IMPORTANTE)
# -------------------------

android.api = 34
android.minapi = 23
android.sdk_build_tools = 34.0.0
android.accept_sdk_license = True

android.ndk = 25b
android.cflags = -D__GNUC_PREREQ(x,y)=0


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2
