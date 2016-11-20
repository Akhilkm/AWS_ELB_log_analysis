import time
import re

start=raw_input("Enter start date(YYYY/mm/dd HH:MM:SS) in UST: ")
end=raw_input("Enter end date(YYYY/mm/dd HH:MM:SS) in UST: ")

pattern = re.compile("[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]")
if pattern.match(start) and pattern.match(end):
	print "Entered start/end time is not in a proper format"
	exit()

prefix = []

start1 = start.split(" ")[0]
end1 = end.split(" ")[0]
next1 = start1

pattern = '%Y/%m/%d %H:%M:%S'
epoch_start = int(time.mktime(time.strptime(start, pattern)))
epoch_end = int(time.mktime(time.strptime(end, pattern)))
epoch_next = epoch_start

while end1>= next1:
	prefix.append(next1)
	epoch_next = epoch_next+24*3600
	next1 = time.strftime("%Y/%m/%d", time.gmtime(epoch_next))

print prefix		
