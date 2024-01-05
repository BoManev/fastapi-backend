#!/usr/bin/env bash

poetry run pyreverse api
dot -Tpng classes.dot -o uml.png
rm classes.dot
rm packages.dot