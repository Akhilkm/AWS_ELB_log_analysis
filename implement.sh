#!/bin/bash



{ echo  "#!"$(which python)"\n"; cat elb_log_analysis.py; } >/usr/bin/elb_log_analysis

chmod +111 /usr/bin/elb_log_analysis
