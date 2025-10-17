#!/bin/bash
coverage run --include=../main.py -m pytest test_main.py
coverage html