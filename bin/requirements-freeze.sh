#!/usr/bin/env sh

pip3 freeze -q -r requirements-prod.txt | sed '/freeze/,$ d' >requirements.txt
