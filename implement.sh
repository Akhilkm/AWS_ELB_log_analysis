#!/bin/bash



{ echo -e  "#!"$(which python)"\n"; cat elb_log_analysis.py; } >/usr/log/elb_log_analysis

chmod +111 /usr/log/elb_log_analysis
